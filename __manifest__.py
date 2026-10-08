{
    'name': 'Porcelia Equipment Loan',

    'sequence': 0,

    'summary': 'Porcelia Equipment Loan System',

    "description": """

Porcelia Equipment Loan System
--------------------------

Porcelia lends equipment to employees: laptops, tile-measuring devices, sample cases and display stands.

This app : 
    - Manages equipements, employee loans.
    - Prevents duplicated reservation.
    - Stores cretical information.
    - Provides useful analytics.
    - Tracks, stores everything related to daily transactions  
    """,

    'version': '18.0.1.0.0',
    'category': 'Services',
    'author': "Islam Mahdy",
    'license': 'LGPL-3',

    'depends': ['base', 'mail'],

    'data': [
        # Security
        'security/equipment_groups.xml',
        'security/equipment_rules.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_cron.xml',
        'data/ir_sequence.xml',
        'data/equipment_demo.xml',


        # Views
        'views/res_users_views.xml',
        'views/equipment_item_views.xml',
        'views/equipment_category_views.xml',
        'views/equipment_loan_views.xml',
        'views/equipment_menus.xml',

        # Reports
        'report/equipment_loan_report.xml',
        'report/equipment_enhanced_report.xml',

        # Wizard views
        'wizard/equipment_loan_return_wizard_views.xml',




    ],

    'installable': True,
    'application': True,
}




