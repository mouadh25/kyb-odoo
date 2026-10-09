# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from unittest.mock import patch


class TestResPartnerKyb(TransactionCase):

    def setUp(self):
        super(TestResPartnerKyb, self).setUp()
        self.partner_model = self.env['res.partner']
        # Setup system parameters
        self.env['ir.config_parameter'].set_param('kyb.api_key', 'test_key_abc')
        self.env['ir.config_parameter'].set_param('kyb.base_url', 'https://kyb.digidevagency.dz')

    @patch('conforme.Conforme')
    def test_onchange_kyb_nif_success(self, mock_conforme_class):
        # Configure mock client instance
        mock_client = mock_conforme_class.return_value
        mock_client.resolve.return_value = {
            'entity': {
                'nif': '123456789012345',
                'raison_sociale': 'Test Company',
                'rc_number': '16/00-999999B26',
                'statut_cnrc': 'ACTIF',
                'activite': 'Software Development',
                'adresse': 'Algiers, Algeria',
                'article_imposition': '16010000001',
                'nis': '000816097764131'
            }
        }

        partner = self.partner_model.create({
            'name': False,
            'kyb_nif': '123456789012345'
        })
        
        # Trigger onchange
        partner._onchange_kyb_nif()

        # Assert correct field mappings
        self.assertEqual(partner.name, 'Test Company')
        self.assertEqual(partner.kyb_rc, '16/00-999999B26')
        self.assertEqual(partner.kyb_statut_cnrc, 'ACTIF')
        self.assertEqual(partner.kyb_activite, 'Software Development')
        self.assertEqual(partner.street, 'Algiers, Algeria')
        self.assertEqual(partner.kyb_article_imposition, '16010000001')
        self.assertEqual(partner.kyb_nis, '000816097764131')
        self.assertTrue(partner.kyb_last_verified)

    @patch('conforme.Conforme')
    def test_onchange_kyb_nif_not_found(self, mock_conforme_class):
        mock_client = mock_conforme_class.return_value
        mock_client.resolve.side_effect = Exception("Not found")

        partner = self.partner_model.create({
            'name': 'Draft Partner',
            'kyb_nif': '000000000000000'
        })

        res = partner._onchange_kyb_nif()
        self.assertIn('warning', res)

    @patch('conforme.Conforme')
    def test_name_search_lazy_creation(self, mock_conforme_class):
        mock_client = mock_conforme_class.return_value
        mock_client.search.autocomplete.return_value = [
            {
                'nif': '123456789012345',
                'raison_sociale': 'Test Lazy Company',
                'rc': '16/00-999999B26',
                'statut_cnrc': 'ACTIF',
                'activite': 'Software Development',
                'adresse': 'Algiers, Algeria'
            }
        ]

        # Make sure no partner exists in database with this NIF
        existing = self.partner_model.search([('kyb_nif', '=', '123456789012345')])
        self.assertFalse(existing)

        # Trigger name search
        res = self.partner_model._name_search(
            name='Test Lazy',
            domain=[],
            operator='ilike',
            limit=10
        )

        # Res should contain a tuple or id list containing the lazy-created partner
        self.assertTrue(res)
        created = self.partner_model.search([('kyb_nif', '=', '123456789012345')])
        self.assertTrue(created)
        self.assertEqual(created.name, 'Test Lazy Company')
