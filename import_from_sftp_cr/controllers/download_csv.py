# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request
import csv
from io import StringIO
import ast


class CsvController(http.Controller):

    @http.route('/web/downloadcsv', type='http', auth="user")
    def export_csv_sample(self, header_list=[], **kw):
        headers_list = ast.literal_eval(header_list)
        csv_buffer = StringIO()

        # Create a CSV writer object
        writer = csv.writer(csv_buffer)

        # Write the list of values to the CSV file
        writer.writerow(headers_list)

        # Create a response object with the CSV contents
        response = request.make_response(csv_buffer.getvalue())

        # Set the content type and attachment header for the response
        response.headers['Content-Disposition'] = 'attachment; filename=sample_data.csv'
        response.headers['Content-type'] = 'text/csv'

        return response
