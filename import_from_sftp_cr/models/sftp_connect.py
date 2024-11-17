# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
import paramiko
import os
from datetime import datetime
import csv
import io
from io import StringIO
from odoo.exceptions import MissingError
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class SftpConfiguration(models.Model):
    _name = 'sftp.connect'
    _rec_name = 'host_name'

    host_name = fields.Char('Host Name', required=True)
    username = fields.Char('Username', required=True)
    password = fields.Char('Password/Passphrase')
    with_password = fields.Boolean('Connect with Password',
            help="Enable if you want to connect using password, if disabled it will connect using public key.",
                                   copy=False)
    public_key_path = fields.Char(string="Public Key Path", copy=False)

    def test_connection(self):
        # Create an SSH client object
        ssh = paramiko.SSHClient()
        # Automatically add the host key
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            # Connect to the remote server
            if self.with_password:
                ssh.connect(self.host_name, username=self.username, password=self.password)
            else:
                ssh.connect(self.host_name, username=self.username, password=self.password,
                            key_filename=self.public_key_path)

            # If the connection was successful, print a success message
            print(f"Successfully connected to {self.host_name}!")
            # Close the SSH connection
            ssh.close()
            message = _("Test Connection Successful!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except paramiko.AuthenticationException:
            raise ValidationError(f"Authentication failed for {self.username}@{self.host_name}")

        except paramiko.SSHException:
            # If there was an SSH-related error, print an error message
            raise ValidationError(f"Unable to establish SSH connection to {self.host_name}")

        except Exception as e:
            # If there was any other type of error, print the exception message
            raise ValidationError(f"Error occurred while connecting to {self.host_name}: {e}")


class SftpImportConfiguration(models.Model):
    _name = 'sftp.import.config'
    _rec_name = 'sftp_host'

    sftp_host = fields.Many2one('sftp.connect', required=True)
    # remote_source_dirpath = fields.Char('Remote Source Directory Path', required=True)
    # remote_archive_dirpath = fields.Char('Remote Archive Directory Path', required=True)
    source_destination_paths = fields.One2many('source.destination.paths', 'sftp_config_id', string="Source Destination Configuration")
    model = fields.Many2one('ir.model')
    fields = fields.One2many('sftp.import.config.fields', 'import_config_id', string='Fields')

    def generate_sample_csv(self):
        for rec in self:
            header_list = []
            if rec.fields:
                # Define the data to be written to the CSV file
                for field_line in rec.fields:
                    header_list.append(field_line.mapping_field)
                return {
                    'name': 'CSV',
                    'type': 'ir.actions.act_url',
                    'url': '/web/downloadcsv?header_list=%(header_list)s' % {'header_list': header_list},
                    }

    def _read_from_sftp_and_import(self):
        import_config_ids = self.search([])
        for import_config in import_config_ids:
            import_config.sftp_host.test_connection()

            hostname = import_config.sftp_host.host_name
            username = import_config.sftp_host.username
            password = import_config.sftp_host.password

            # remote_source_dirpath = import_config.remote_source_dirpath
            # remote_archive_dirpath = import_config.remote_archive_dirpath
            # create an SSH client object
            ssh = paramiko.SSHClient()

            # automatically add the server's host key
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if import_config.sftp_host.with_password:
                ssh.connect(hostname,username, password=password)
            else:
                ssh.connect(hostname, username=username, password=password, key_filename=import_config.sftp_host.public_key_path)

            for path in import_config.source_destination_paths:
                # open an SFTP session
                sftp = ssh.open_sftp()
                try:
                    # list the files in a directory
                    files = sftp.listdir(path.remote_source_dirpath)
                    import_list = []
                    for file in files:
                        if ' ' not in file and (file.endswith('.csv') or file.endswith('.xls') or file.endswith('.xlsx')):
                            import_list.append(file)

                except paramiko.SSHException as e:
                    # handle SSH exceptions
                    raise ValidationError(f"SSH error: {e}")

                except IOError as e:
                    # handle IO exceptions
                    raise ValidationError(f"IO error: {e}")

                except Exception as e:
                    # handle all other exceptions
                    raise ValidationError("Error:", e)
                # download a file
                for f in import_list:
                    if ' ' not in f and (f.endswith('.csv') or f.endswith('.xls') or f.endswith('.xlsx')):
                        remote_file = (path.remote_source_dirpath if path.remote_source_dirpath.endswith('/') else path.remote_source_dirpath+'/')  + f
                        # Open the CSV file and read its contents
                        with sftp.open(remote_file) as open_file:
                            # Read the content of the file
                            file_content = open_file.read()

                            # Create a BytesIO object to work with the file content
                            csv_content = io.BytesIO(file_content)

                            # Decode the bytes content using the specified encoding
                            decoded_content = csv_content.read().decode('Latin-1')

                            # Create a StringIO object from the decoded content
                            csv_data = io.StringIO(decoded_content)

                            csv_row = csv.DictReader(csv_data)

                            line = 0
                            not_updated = []

                            for roww in csv_row:
                                roww = {x.strip().lower(): v for x, v in roww.items()}
                                lead_vals = {f.field.name: roww.get(f.mapping_field.lower()) for f in import_config.fields}
                                selection_fields = [field.name for field in import_config.model.field_id if field.ttype=='selection']
                                for k,v in lead_vals.items():
                                    if k in selection_fields:
                                        selection_values = self.env[import_config.model.model]._fields[k].selection
                                        for key,val in selection_values:
                                            if v == val:
                                                lead_vals[k] = key
                                _logger.info('lead vals ----------------->%s --',lead_vals)
                                lead_create = self.env[import_config.model.model].create(lead_vals)
                                if not lead_create:
                                    not_updated.append(lead_vals)
                                line += 1

                        # make date wise name new directory in order to move the file
                        date_str = datetime.now().strftime('%Y-%m-%d')
                        new_dir = os.path.join((path.remote_archive_dirpath if path.remote_archive_dirpath.endswith('/') else path.remote_archive_dirpath+'/'), date_str)
                        if date_str not in sftp.listdir(path.remote_archive_dirpath):
                            sftp.mkdir(new_dir)

                        # move files from one to another folder
                        sftp.posix_rename(remote_file, new_dir+'/'+f)
                    else:
                        raise MissingError('No file found for Import!')

                # close the SFTP session and the SSH connection
                self.env.cr.commit()
                sftp.close()
        ssh.close()


class SftpImportConfigurationFields(models.Model):
    _name = 'sftp.import.config.fields'
    _rec_name = 'import_config_id'

    import_config_id = fields.Many2one('sftp.import.config', 'sftp Import Config')
    field = fields.Many2one("ir.model.fields",
                            domain=[('ttype', 'in', ['char', 'boolean', 'float', 'integer', 'reference', 'text'])])
    mapping_field = fields.Char()

    @api.onchange("field")
    def _onchange_field(self):
        if self.field:
            self.mapping_field = self.field.field_description
        else:
            self.mapping_field = False


class SftpSourceDesctinationPaths(models.Model):
    _name = 'source.destination.paths'
    _rec_name = 'sftp_config_id'

    sftp_config_id = fields.Many2one('sftp.import.config', string="Sftp Import Config")
    remote_source_dirpath = fields.Char('Source Directory', required=True)
    remote_archive_dirpath = fields.Char('Archive Directory', required=True)