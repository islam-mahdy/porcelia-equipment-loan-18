import math
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

MANAGER_GROUP = 'porcelia_equipment_loan.group_equipment_manager'
SECONDS_PER_DAY = 86400.0


def _ceil_days(delta):
    return math.ceil(delta.total_seconds() / SECONDS_PER_DAY)


class EquipmentLoan(models.Model):
    _name = 'equipment.loan'
    _description = 'Equipment Loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Reference', required=True, copy=False,
        readonly=True, default='New'
    )
    item_id = fields.Many2one(
        'equipment.item', required=True, index=True,
        tracking=True, ondelete='restrict'
    )
    borrower_id = fields.Many2one(
        'res.users', string='Borrower',
        required=True, index=True, tracking=True,
        default=lambda self: self.env.user
    )
    company_id = fields.Many2one(
        related='item_id.company_id', store=True, index=True
    )
    currency_id = fields.Many2one(
        related='item_id.currency_id', store=True
    )
    date_start = fields.Datetime(
        required=True, default=fields.Datetime.now, tracking=True
    )
    date_due = fields.Datetime(
        required=True, tracking=True,
        default=lambda self: fields.Datetime.now() + timedelta(days=1)
    )
    date_return = fields.Datetime(copy=False, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled')
    ], default='draft', required=True,
        copy=False, tracking=True, index=True
    )

    days_late = fields.Integer(compute='_compute_days_late', store=True)

    penalty_amount = fields.Monetary(
        compute='_compute_penalty_amount', store=True, currency_field='currency_id'
    )
    days_on_loan = fields.Integer(
        compute='_compute_days_on_loan', store=True,
        help="Duration of the loan in days (actual if returned, planned otherwise)."
    )
    is_overdue = fields.Boolean(
        copy=False, index=True,
    )
    notes = fields.Html()


    def _is_manager(self):
        return self.env.user.has_group(MANAGER_GROUP)

    def _check_manager(self):
        if not self._is_manager():
            raise AccessError(
                _("Only Equipment Managers can perform this action.")
            )

    def _check_state(self, allowed):
        for loan in self:
            if loan.state not in allowed:
                raise UserError(
                    _(
                        f"Loan {loan.name} is in state '{loan.state}'; "
                        "this action is not allowed.",
                    )
                )

    # Computes methods
    @api.depends('date_due', 'date_return')
    def _compute_days_late(self):
        for loan in self:
            if loan.date_return and loan.date_due and loan.date_return > loan.date_due:
                loan.days_late = _ceil_days(loan.date_return - loan.date_due)
            else:
                loan.days_late = 0

    @api.depends('days_late', 'item_id.daily_rate')
    def _compute_penalty_amount(self):
        for loan in self:
            loan.penalty_amount = loan.days_late * loan.item_id.daily_rate

    @api.depends('date_start', 'date_due', 'date_return', 'state')
    def _compute_days_on_loan(self):
        for loan in self:
            end = loan.date_return or loan.date_due
            if loan.state in ('confirmed', 'returned') and loan.date_start and end:
                loan.days_on_loan = max(0, _ceil_days(end - loan.date_start))
            else:
                loan.days_on_loan = 0

    # Constraints

    @api.constrains('date_start', 'date_due', 'date_return')
    def _check_dates(self):
        for loan in self:
            if loan.date_start and loan.date_due and loan.date_due <= loan.date_start:
                raise ValidationError(
                    _("The due date must be after the start date.")
                )
            if loan.date_return and loan.date_start and loan.date_return < loan.date_start:
                raise ValidationError(
                    _("The return date cannot be before the start date.")
                )

    # Check no double Loans
    @api.constrains('item_id', 'date_start', 'date_due', 'state', 'date_return')
    def _check_no_overlap(self):
        # Loans without known return date
        loans = self.filtered(lambda l: l.state == 'confirmed' and not l.date_return)
        for loan in loans:
            conflict = self.search([
                ('id', '!=', loan.id),
                ('item_id', '=', loan.item_id.id),
                ('state', '=', 'confirmed'),
                ('date_return', '=', False),
                ('date_start', '<', loan.date_due),
                ('date_due', '>', loan.date_start),
            ], limit=1)
            if conflict:
                raise ValidationError(_(
                    f"{loan.item_id.display_name} is already booked by loan {conflict.name} "
                    f"{fields.Datetime.to_string(conflict.date_start)} -> {fields.Datetime.to_string(conflict.date_due)}.",
                    ))

    # ORM overrides

    @api.model_create_multi
    def create(self, vals_list):
        if not self._is_manager() and any(
                vals.get('state', 'draft') != 'draft' for vals in vals_list):
            raise UserError(
                _("Loan requests must be created in draft state.")
            )
        for vals in vals_list:
            if not vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('equipment.loan') or 'New Equipment Loan'
        return super().create(vals_list)


    def write(self, vals):
        if not self._is_manager() and any(loan.state != 'draft' for loan in self):
            raise UserError(
                _("Only managers can modify a loan that is no longer in draft.")
            )
        return super().write(vals)


    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancelled(self):
        if any(loan.state not in ('draft', 'cancelled') for loan in self):
            raise UserError(
                _("Only draft or cancelled loans can be deleted.")
            )


    # Workflow Methods
    def action_confirm(self):
        self._check_manager()
        self._check_state(('draft',))
        for loan in self:
            if loan.item_id.unavailable_state:
                raise UserError(
                    _("{loan.item_id.display_name} is out of service ({loan.item_id.unavailable_state}) and cannot be loaned.",
                    ))
            # loan._check_no_overlap()
            loan.state =  'confirmed'


    def action_return(self, date_return=None):
        self._check_manager()
        self._check_state(('confirmed',))
        self.write({
            'state': 'returned',
            'date_return': date_return or fields.Datetime.now(),
            'is_overdue': False,
        })


    def action_cancel(self):
        self._check_state(('draft', 'confirmed'))
        self.write({'state': 'cancelled', 'is_overdue': False})


    def action_draft(self):
        self._check_manager()
        self._check_state(('cancelled',))
        self.write({'state': 'draft'})


    # Cron

    @api.model
    def _cron_check_overdue(self):
        now = fields.Datetime.now()
        loans = self.search([
            ('state', '=', 'confirmed'),
            ('date_return', '=', False),
            ('date_due', '<', now),
            ('is_overdue', '=', False),
        ])
        for loan in loans:
            loan.is_overdue = True


            # From Internet I did not study it yet.

            loan.message_post(body=_(
                "This loan is overdue since %s.",
                fields.Datetime.to_string(loan.date_due)))
            loan.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=loan.borrower_id.id,
                summary=_("Return %s", loan.item_id.display_name),
                note=_("Loan %(loan)s was due on %(due)s. Please return the item.",
                       loan=loan.name, due=fields.Datetime.to_string(loan.date_due)))

