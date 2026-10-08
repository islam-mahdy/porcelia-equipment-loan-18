from odoo import _, fields, models
from odoo.exceptions import UserError


class EquipmentLoanReturnWizard(models.TransientModel):
    _name = 'equipment.loan.return.wizard'
    _description = 'Equipment Loan Return Wizard'

    loan_ids = fields.Many2many(
        'equipment.loan',
        string='Loans'
    )

    date_return = fields.Datetime(
        string='Return Date',
        required=True,
        default=fields.Datetime.now
    )

    condition_score = fields.Integer(
        string='Condition Score',
        default=100,
        required=True
    )

    note = fields.Text(
        string='Note'
    )

    def action_confirm(self):
        self.ensure_one()

        loan_ids = self.env.context.get('active_ids', [])

        loans = self.env['equipment.loan'].browse(loan_ids)

        loans = loans.filtered(
            lambda loan: loan.state == 'confirmed'
        )

        if not loans:
            raise UserError(
                _("Please select at least one confirmed loan.")
            )

        loans.action_return(
            date_return=self.date_return
        )

        for loan in loans:
            loan.item_id.write({
                'condition_score': self.condition_score,
            })

            body = _(
                "Equipment returned. Condition Score: %(score)s",
                score=self.condition_score
            )

            if self.note:
                body += "\n" + self.note

            loan.message_post(
                body=body
            )

        return {
            'type': 'ir.actions.act_window_close'
        }