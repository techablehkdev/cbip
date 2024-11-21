# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.
{
    'name': "Import Data from SFTP File",
    'version': "15.0.0.0",
    'category': "Extra Tools",
    'author': 'Candidroot Solutions Pvt. Ltd.',
    'website': 'https://www.candidroot.com',
    'summary': 'Import Data from SFTP File',
    'description': '''
             This module allows you to import file hosted on SFTP server and move imported file to another folder.
    ''',
#    'depends': ['base','crm'],
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/sftp_import_file.xml',
        'views/sftp_connect_view.xml',
    ],
    'assets': {},
    'images': ['static/description/banner.jpeg'],
    'price': 149.99,
    'currency': 'USD',
    'live_test_url': 'https://youtu.be/G4gx8QPGlow',
    'installable': True,
    'auto_install': False,
    'application': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
