# -*- coding: utf-8 -*-
"""
KYB Configuration Settings — Enterprise settings panel for KYB API (by Digidev) credentials.
Allows configuring API keys and Gateway URLs without requiring Developer Mode.
"""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    kyb_api_key = fields.Char(
        string="KYB Secret API Key",
        config_parameter="kyb.api_key",
        help="Clé d'API secrète KYB (e.g. sk_live_... pour la production ou sk_test_kyb_sandbox_key_001 pour le bac à sable gratuit).",
    )
    kyb_base_url = fields.Char(
        string="KYB Gateway Base URL",
        config_parameter="kyb.base_url",
        default="https://kyb.digidevagency.dz",
        help="URL du gateway souverain KYB (par défaut: https://kyb.digidevagency.dz).",
    )
    kyb_sovereign_autocomplete = fields.Boolean(
        string="CNRC Autocomplete",
        config_parameter="kyb.sovereign_autocomplete",
        default=True,
        help="Intercepts company name searches to query the Algerian CNRC registry instead of offshore Odoo IAP / Dun & Bradstreet servers.",
    )
    kyb_allow_worldwide_fallback = fields.Boolean(
        string="Allow Worldwide Fallback",
        config_parameter="kyb.allow_worldwide_fallback",
        default=False,
        help="Allows fallback to international search when specifically clicking 'Search Worldwide'.",
    )
    kyb_duplicate_nif_policy = fields.Selection(
        selection=[
            ("warn", "Avertissement (Notifier la présence d'un contact existant)"),
            ("block", "Blocage Strict (Interdire la duplication du NIF)"),
            ("ignore", "Ignorer (Comportement natif Odoo multi-établissements)"),
        ],
        string="Détection des Doublons Fiscaux (NIF)",
        config_parameter="kyb.duplicate_nif_policy",
        default="warn",
        help="Contrôle le comportement lorsqu'un NIF saisi existe déjà sur une autre fiche partenaire.",
    )
    kyb_invoice_audit_enabled = fields.Boolean(
        string="Audit Temporel des Factures",
        config_parameter="kyb.invoice_audit_enabled",
        default=True,
        help="Contrôle automatiquement la conformité temporelle (Art. 169 & 176 CIDTA / Art. 30 CTCA) sur les factures d'achat.",
    )
    kyb_invoice_blocking_policy = fields.Selection(
        selection=[
            ("strict_block", "Blocage Strict (Interdire la comptabilisation si radié)"),
            ("soft_warn", "Avertissement (Consignation dans le Chatter sans blocage)"),
            ("warning", "Avertissement (Consignation dans le Chatter sans blocage)"),
        ],
        string="Politique de Validation des Factures",
        config_parameter="kyb.invoice_blocking_policy",
        default="strict_block",
        help="Comportement lors de la confirmation d'une facture d'achat pour un fournisseur radié.",
    )
    kyb_unverified_partner_policy = fields.Selection(
        selection=[
            ("allow_warn", "Autoriser avec avertissement 'Non Vérifié'"),
            ("require_verify", "Exiger la vérification KYB préalable"),
        ],
        string="Politique Fournisseurs Non Vérifiés",
        config_parameter="kyb.unverified_partner_policy",
        default="allow_warn",
        help="Comportement lors de la saisie d'un fournisseur n'ayant pas encore été vérifié sur le registre.",
    )
    kyb_eom_auto_audit = fields.Boolean(
        string="Audit Automatique de Clôture Mensuelle G50",
        config_parameter="kyb.eom_auto_audit",
        default=True,
        help="Déclenche une tâche planifiée mensuelle pour auditer l'ensemble des factures du mois avant déclaration G50.",
    )
    kyb_eom_audit_day = fields.Integer(
        string="Jour du mois pour l'audit G50",
        config_parameter="kyb.eom_audit_day",
        default=18,
        help="Jour du mois auquel l'audit automatique est exécuté (par défaut le 18, avant la date limite fiscale du 20).",
    )

