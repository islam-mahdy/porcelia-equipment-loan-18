from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EquipmentItem(models.Model):
    _name = 'equipment.item'
    _description = 'Equipment Item'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'code'

    name = fields.Char(required=True)
    code = fields.Char(
        required=True, copy=False,
        readonly=True, default='New'
    )
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        'res.company', required=True, index=True,
        default=lambda self: self.env.company
    )
    category_id = fields.Many2one(
        'equipment.category',
        string='Category', index=True
    )

    currency_id = fields.Many2one(
        'res.currency', required=True,
        default=lambda self: self.env.company.currency_id
    )
    daily_rate = fields.Monetary(
        string='Daily Late Rate', currency_field='currency_id',
        help="Penalty charged per day of delay when the item is returned late."
    )
    condition_score = fields.Integer(
        default=100, help="0 (broken) to 100 (as new)."
    )
    unavailable_state = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('scrapped', 'Scrapped')
    ], string='Out of Service', copy=False,
     help="Manual override: the item cannot be loaned while set."
    )

    state = fields.Selection([
        ('available', 'Available'),
        ('on_loan', 'On Loan'),
        ('maintenance', 'Maintenance'),
        ('scrapped', 'Scrapped')
    ], compute='_compute_state', store=True, index=True
    )

    loan_ids = fields.One2many(
        'equipment.loan', 'item_id',
        string='Loans'
    )
    loan_count = fields.Integer(compute='_compute_loan_count')

    total_days_on_loan = fields.Integer(compute='_compute_total_days_on_loan')

    _sql_constraints = [
        (
            'code_company_unique', 'unique(code, company_id)',
            'The item code must be unique per company.'
        ),
        (
            'condition_score_range', 'CHECK(condition_score BETWEEN 0 AND 100)',
             'The condition score must be between 0 and 100.'
        ),
    ]

    # Compute Methods
    @api.depends('unavailable_state', 'loan_ids.state', 'loan_ids.date_return')
    def _compute_state(self):
        for item in self:
            if item.unavailable_state:
                item.state = item.unavailable_state
            elif any(loan.state == 'confirmed' and not loan.date_return
                     for loan in item.loan_ids):
                item.state = 'on_loan'
            else:
                item.state = 'available'

    @api.depends('loan_ids')
    def _compute_loan_count(self):
        for item in self:
            item.loan_count = len(item.loan_ids)

    @api.depends('loan_ids.days_on_loan', 'loan_ids.state')
    def _compute_total_days_on_loan(self):
        for item in self:
            loans = item.loan_ids.filtered(
                lambda loan: loan.state in ('confirmed', 'returned')
            )

            item.total_days_on_loan = sum(
                loans.mapped('days_on_loan')
            )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New' == 'New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('equipment.item') or 'New Equipment Item'
        return super().create(vals_list)

    # actions
    def action_view_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _(f"Loans of {self.name}"),
            'res_model': 'equipment.loan',
            'view_mode': 'list,form',
            'domain': [('item_id', '=', self.id)],
            'context': {'default_item_id': self.id},
        }

    def _check_not_on_loan(self):
        for item in self:
            if item.state == 'on_loan':
                raise UserError(
                    _(f"{item.name} is currently on loan.")
                )

    def action_set_maintenance(self):
        self._check_not_on_loan()
        self.unavailable_state = 'maintenance'

    def action_scrap(self):
        self._check_not_on_loan()
        self.unavailable_state = 'scrapped'

    def action_back_in_service(self):
        self.unavailable_state = False
