###############################################################################
#                                                                             #
# Copyright (C) 2016  Dominic Krimmer                                         #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU Affero General Public License for more details.                         #
#                                                                             #
# You should have received a copy of the GNU Affero General Public License    #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
###############################################################################

# Extended Partner Module
from odoo import models, fields, api, exceptions
from odoo.tools.translate import _
import re
import logging
_logger = logging.getLogger(__name__)



class PartnerInfoExtended(models.Model):
	_name = 'res.partner'
	_inherit = 'res.partner'

	# Brand Name (e.j. Claro Móvil = Brand, COMCEL SA = legal name)
	companyBrandName = fields.Char(string="Nombre del establecimiento")
	# Tributate regime
	x_pn_retri = fields.Selection(selection =
									[
										("6", "Simplified"),
										("23", "Natural Person"),
										("7", "Common"),
										("11", "Great Taxpayer Autorretenedor"),
										("22", "International"),
										("25", "Common Autorretenedor"),
										("24", "Great Contributor")
									], 
									string="Tax Regime",
									default="6"                                    
								  )
	# CIIU - Clasificación Internacional Industrial Uniforme
	ciiu = fields.Many2one('ciiu', string="Actividad de la CIIU")
	# Check to handle change of Country, City and Municipality
	change_country = fields.Boolean(string="Change Country / Department?",
									default=True, store=False)
	# Birthday of the contact (only useful for non-company contacts)
	xbirthday = fields.Date(string="Fecha de nacimiento")

	@api.onchange('firstname', 'other_name', 'lastname', 'other_lastname')
	def _concat_name(self):
		"""
				This function concatenates the four name fields in order to be able to
				search for the entire name. On the other hand the original name field
				should not be editable anymore as the new name fields should fill it up
				automatically.
				@return: void
				"""
		# Avoiding that "False" will be written into the name field
		if not self.firstname:
			self.firstname = ''

		if not self.other_name:
			self.other_name = ''

		if not self.lastname:
			self.lastname = ''

		if not self.other_lastname:
			self.other_lastname = ''

		if self.firstname:
			self.firstname = self.firstname.upper()
		if self.other_name:
			self.other_name = self.other_name.upper()
		if self.lastname:
			self.lastname = self.lastname.upper()
		if self.other_lastname:
			self.other_lastname = self.self.other_lastname.upper()

		# Collecting all names in a field that will be concatenated
		nameList = [
			self.firstname.encode(encoding='utf-8').strip(),
			self.other_name.encode(encoding='utf-8').strip(),
			self.lastname.encode(encoding='utf-8').strip(),
			self.other_lastname.encode(encoding='utf-8').strip()
		]


	@api.onchange('change_country')
	def on_change_address(self):
		"""
		This function changes the person type field and the company type if
		checked / unchecked
		@return: void
		"""
		if self.change_country is True:
			self.country_id = False
			self.state_id = False
			self.city_id = False

	def _check_dv(self, nit):
		"""
		Function to calculate the check digit (DV) of the NIT. So there is no
		need to type it manually.
		@param nit: Enter the NIT number without check digit
		@return: String
		"""
		for item in self:
			if item.l10n_latam_identification_type_id.l10n_co_document_code != "rut":
				return str(nit)

			nitString = '0'*(15-len(nit)) + nit
			vl = list(nitString)
			result = (
							 int(vl[0])*71 + int(vl[1])*67 + int(vl[2])*59 + int(vl[3])*53 +
							 int(vl[4])*47 + int(vl[5])*43 + int(vl[6])*41 + int(vl[7])*37 +
							 int(vl[8])*29 + int(vl[9])*23 + int(vl[10])*19 + int(vl[11])*17 +
							 int(vl[12])*13 + int(vl[13])*7 + int(vl[14])*3
					 ) % 11

			if result in (0, 1):
				return str(result)
			else:
				return str(11-result)

	def onchange_location(self, cr, uid, ids, country_id=False,
						  state_id=False):
		"""
		This functions is a great helper when you enter the customer's
		location. It solves the problem of various cities with the same name in
		a country
		@param country_id: Country Id (ISO)
		@param state_id: State Id (ISO)
		@return: object
		"""
		if country_id:
			mymodel = 'res.country.state'
			filter_column = 'country_id'
			check_value = country_id
			domain = 'state_id'

		elif state_id:
			mymodel = 'res.country.state.city'
			filter_column = 'state_id'
			check_value = state_id
			domain = 'city_id'
		else:
			return {}

		obj = self.pool.get(mymodel)
		ids = obj.search(cr, uid, [(filter_column, '=', check_value)])
		return {
			'domain': {domain: [('id', 'in', ids)]},
			'value': {domain: ''}
		}

	'''@api.constrains('vat_num')
	def _check_ident(self):
		"""
		This function checks the number length in the Identification field.
		Min 6, Max 12 digits.
		@return: void
		"""
		partner_ids = self.env['res.partner'].search([('vat_num', '=', '')])
		data = []
		if partner_ids:
			for x in partner_ids:
				data.append(x.id)
		_logger.info(data)
		for item in self:
			if item.l10n_latam_identification_type_id is not "false":
				msg = _('¡Error! El número de dígitos del número de identificación debe ser entre 2 y 12')
				
				_logger.info(item.id)
				_logger.info(item.name)
				_logger.info((str(item.vat_num)))
				_logger.info(len(str(item.vat_num)))
				if len(str(item.vat_num)) < 2:
					raise exceptions.ValidationError(msg)
				elif len(str(item.vat_num)) > 30:
					raise exceptions.ValidationError(msg)'''

	@api.constrains('vat_num')
	def _check_ident_num(self):
		"""
		This function checks the content of the identification fields: Type of
		document and number cannot be empty.
		There are two document types that permit letters in the identification
		field: 21 and 41. The rest does not permit any letters
		@return: void
		"""
		for item in self:
			if item.l10n_latam_identification_type_id is not "false":
				if item.vat_num is not False and \
						item.l10n_latam_identification_type_id.l10n_co_document_code != "foreign_id_card" and \
						item.l10n_latam_identification_type_id.l10n_co_document_code != "passport" and item.l10n_latam_identification_type_id.l10n_co_document_code != "external_id":
					if re.match("^[0-9]+$", item.vat_num) is None:
						msg = _('¡Error! El número de identificación solo puede tener números')
						raise exceptions.ValidationError(msg)

	def change_vat_type_nit(self, partner):
		if partner.l10n_latam_identification_type_id.l10n_co_document_code == 'rut':
			return '31'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'id_document':
			return '13'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'id_card':
			return '12'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'passport':
			return '41'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'foreign_id_card':
			return '22'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'external_id':
			return '50'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'diplomatic_card':
			return ''
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'residence_document':
			return ''
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'civil_registration':
			return '11'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'national_citizen_id':
			return '13'
		elif partner.l10n_latam_identification_type_id.l10n_co_document_code == 'niup_id':
			return '91'

	def change_vat_type_dos_nit(self, partner):
		if partner.vat_type == '31':
			return 'rut'
		elif partner.vat_type == '13':
			return 'id_document'
		elif partner.vat_type == '12':
			return 'id_card'
		elif partner.vat_type == '41':
			return 'passport'
		elif partner.vat_type == '22':
			return 'foreign_id_card'
		elif partner.vat_type == '50':
			return 'external_id'
		elif partner.vat_type == '91':
			return 'niup_id'
		elif partner.vat_type == '':
			return ''
		elif partner.vat_type == '11':
			return 'civil_registration'
		elif partner.vat_type == '13':
			return 'national_citizen_id'



	def _display_address(self, without_company=False):

		'''
		The purpose of this function is to build and return an address formatted accordingly to the
		standards of the country where it belongs.

		:param address: browse record of the res.partner to format
		:returns: the address formatted in a display that fit its country habits (or the default ones
			if not country is specified)
		:rtype: string
		'''
		# get the information that will be injected into the display format
		# get the address format
		address_format = self._get_address_format()
		args = {
			'state_code': self.state_id.code or '',
			'state_name': self.state_id.name or '',
			'country_code': self.country_id.code or '',
			'country_name': self._get_country_name(),
			'company_name': self.commercial_company_name or '',
		}
		for field in self._formatting_address_fields():
			args[field] = getattr(self, field) or ''
		if without_company:
			args['company_name'] = ''
		elif self.commercial_company_name:
			address_format = '%(company_name)s\n' + address_format

		args['city'] = args['city'].capitalize() + ','
		return address_format % args
