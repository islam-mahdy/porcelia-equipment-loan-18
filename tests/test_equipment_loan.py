from datetime import datetime, timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestEquipmentLoan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Loan = cls.env['equipment.loan']
        cls.Item = cls.env['equipment.item']
        cls.Category = cls.env['equipment.category']

        cls.manager_group = cls.env.ref(
            'porcelia_equipment_loan.group_equipment_manager'
        )

        cls.manager = cls.env['res.users'].create({
            'name': 'Equipment Manager',
            'login': 'equipment_manager_loan_test',
            'email': 'equipment_manager_loan_test@example.com',
            'groups_id': [(6, 0, [cls.manager_group.id])],
        })

        cls.category = cls.Category.create({
            'name': 'Laptops',
        })

        cls.item = cls.Item.create({
            'name': 'Dell Latitude',
            'category_id': cls.category.id,
            'daily_rate': 50.0,
        })

    def create_loan(self, **values):
        vals = {
            'item_id': self.item.id,
            'borrower_id': self.env.user.id,
            'date_start': '2026-09-27 08:00:00',
            'date_due': '2026-09-29 08:00:00',
        }

        vals.update(values)

        return self.Loan.create(vals)

    def test_loan_creation(self):
        loan = self.create_loan()

        self.assertTrue(loan)
        self.assertEqual(
            loan.state,
            'draft',
        )

        self.assertTrue(
            loan.name,
        )

    def test_non_manager_can_create_only_draft(self):
        loan = self.create_loan()

        self.assertEqual(
            loan.state,
            'draft',
        )

        with self.assertRaises(UserError):
            self.Loan.create({
                'item_id': self.item.id,
                'state': 'confirmed',
                'date_start': '2026-09-27 08:00:00',
                'date_due': '2026-09-29 08:00:00',
            })

    def test_manager_can_create_confirmed_loan(self):
        loan = self.Loan.with_user(self.manager).create({
            'item_id': self.item.id,
            'borrower_id': self.env.user.id,
            'state': 'confirmed',
            'date_start': '2026-09-27 08:00:00',
            'date_due': '2026-09-29 08:00:00',
        })

        self.assertEqual(
            loan.state,
            'confirmed',
        )

    def test_confirm_loan(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        self.assertEqual(
            loan.state,
            'confirmed',
        )

    def test_non_manager_cannot_confirm(self):
        loan = self.create_loan()

        with self.assertRaises(AccessError):
            loan.action_confirm()

    def test_return_loan(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        return_date = datetime(2026, 9, 29, 10, 0, 0)

        loan.with_user(self.manager).action_return(
            date_return=return_date
        )

        self.assertEqual(
            loan.state,
            'returned',
        )

        self.assertEqual(
            loan.date_return,
            return_date,
        )

        self.assertFalse(
            loan.is_overdue,
        )

    def test_cancel_draft_loan(self):
        loan = self.create_loan()

        loan.action_cancel()

        self.assertEqual(
            loan.state,
            'cancelled',
        )

    def test_cancel_confirmed_loan(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        loan.action_cancel()

        self.assertEqual(
            loan.state,
            'cancelled',
        )

    def test_restore_cancelled_loan_to_draft(self):
        loan = self.create_loan()

        loan.action_cancel()

        loan.with_user(self.manager).action_draft()

        self.assertEqual(
            loan.state,
            'draft',
        )

    def test_invalid_due_date(self):
        with self.assertRaises(ValidationError):
            self.create_loan(
                date_start='2026-09-29 08:00:00',
                date_due='2026-09-28 08:00:00',
            )

    def test_return_before_start_date(self):
        with self.assertRaises(ValidationError):
            self.create_loan(
                date_start='2026-09-29 08:00:00',
                date_due='2026-09-30 08:00:00',
                date_return='2026-09-28 08:00:00',
            )

    def test_days_late_zero_when_returned_on_time(self):
        loan = self.create_loan(
            date_return='2026-09-29 08:00:00',
        )

        self.assertEqual(
            loan.days_late,
            0,
        )

    def test_days_late(self):
        loan = self.create_loan(
            date_return='2026-10-01 08:00:00',
        )

        self.assertEqual(
            loan.days_late,
            2,
        )

    def test_days_late_rounds_up_partial_day(self):
        loan = self.create_loan(
            date_return='2026-10-01 12:00:00',
        )

        self.assertEqual(
            loan.days_late,
            3,
        )

    def test_penalty_amount(self):
        loan = self.create_loan(
            date_return='2026-10-01 08:00:00',
        )

        self.assertEqual(
            loan.days_late,
            2,
        )

        self.assertEqual(
            loan.penalty_amount,
            100.0,
        )

    def test_days_on_loan_confirmed(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        self.assertEqual(
            loan.days_on_loan,
            2,
        )

    def test_days_on_loan_returned(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        loan.with_user(self.manager).action_return(
            date_return='2026-10-01 08:00:00'
        )

        self.assertEqual(
            loan.days_on_loan,
            4,
        )

    def test_draft_loan_has_zero_days_on_loan(self):
        loan = self.create_loan()

        self.assertEqual(
            loan.days_on_loan,
            0,
        )

    def test_overlap_is_rejected(self):
        first_loan = self.create_loan()

        first_loan.with_user(self.manager).action_confirm()

        second_loan = self.create_loan(
            date_start='2026-09-28 08:00:00',
            date_due='2026-09-30 08:00:00',
        )

        with self.assertRaises(ValidationError):
            second_loan.with_user(self.manager).action_confirm()

    def test_non_overlapping_loans_are_allowed(self):
        first_loan = self.create_loan(
            date_start='2026-09-27 08:00:00',
            date_due='2026-09-29 08:00:00',
        )

        first_loan.with_user(self.manager).action_confirm()

        first_loan.with_user(self.manager).action_return(
            date_return='2026-09-29 08:00:00'
        )

        second_loan = self.create_loan(
            date_start='2026-09-29 08:00:00',
            date_due='2026-10-01 08:00:00',
        )

        second_loan.with_user(self.manager).action_confirm()

        self.assertEqual(
            second_loan.state,
            'confirmed',
        )

    def test_unavailable_item_cannot_be_confirmed(self):
        self.item.action_set_maintenance()

        loan = self.create_loan()

        with self.assertRaises(UserError):
            loan.with_user(self.manager).action_confirm()

    def test_delete_draft_loan(self):
        loan = self.create_loan()

        loan.unlink()

        self.assertFalse(
            self.Loan.search([
                ('id', '=', loan.id),
            ])
        )

    def test_delete_cancelled_loan(self):
        loan = self.create_loan()

        loan.action_cancel()
        loan.unlink()

        self.assertFalse(
            self.Loan.search([
                ('id', '=', loan.id),
            ])
        )

    def test_confirmed_loan_cannot_be_deleted(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        with self.assertRaises(UserError):
            loan.unlink()

    def test_returned_loan_cannot_be_deleted(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        loan.with_user(self.manager).action_return(
            date_return='2026-09-29 08:00:00'
        )

        with self.assertRaises(UserError):
            loan.unlink()

    def test_non_manager_cannot_modify_confirmed_loan(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        with self.assertRaises(UserError):
            loan.write({
                'notes': 'Trying to modify confirmed loan.',
            })

    def test_manager_can_modify_confirmed_loan(self):
        loan = self.create_loan()

        loan.with_user(self.manager).action_confirm()

        loan.with_user(self.manager).write({
            'notes': 'Updated by manager.',
        })

        self.assertEqual(
            loan.notes,
            'Updated by manager.',
        )

    def test_cron_marks_overdue_loan(self):
        loan = self.Loan.with_user(self.manager).create({
            'item_id': self.item.id,
            'borrower_id': self.env.user.id,
            'state': 'confirmed',
            'date_start': '2026-09-20 08:00:00',
            'date_due': '2026-09-21 08:00:00',
        })

        loan.is_overdue = False

        self.Loan._cron_check_overdue()

        self.assertTrue(
            loan.is_overdue,
        )