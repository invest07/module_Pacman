# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NqmDocument(models.Model):
    _name = 'nqm.document'
    _description = 'Document réseau / configuration / validation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'document_type, name'

    name = fields.Char(string='Titre du document', required=True, tracking=True)
    ref = fields.Char(string='Référence', readonly=True, default='Nouveau', copy=False)
    project_id = fields.Many2one(
        'nqm.network.project', string='Projet', required=True, tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner', string='Client', related='project_id.partner_id', store=True
    )

    # ─── Type de document ──────────────────────────────────────────────────────
    document_type = fields.Selection([
        # Plans & Architecture
        ('ip_plan', '🌐 Plan d\'adressage IP / VLSM'),
        ('vlan_plan', '🔀 Plan VLAN & Segmentation'),
        ('topology', '🗺️ Schéma de topologie réseau'),
        ('physical_plan', '🔌 Plan de câblage physique'),
        # Configuration
        ('config_router', '⚙️ Configuration routeur'),
        ('config_switch', '⚙️ Configuration switch'),
        ('config_firewall', '🔥 Configuration firewall'),
        ('config_wifi', '📡 Configuration Wi-Fi'),
        ('config_vpn', '🔐 Configuration VPN'),
        ('config_other', '⚙️ Autre config équipement'),
        # Sécurité
        ('hardening', '🛡️ Guide de durcissement'),
        ('security_policy', '📜 Politique de sécurité'),
        ('risk_matrix', '⚠️ Matrice des risques'),
        # Tests & Validation
        ('test_plan', '🧪 Plan de tests'),
        ('test_report', '📊 Rapport de tests'),
        ('validation_form', '✅ Fiche de validation'),
        # Livraison
        ('user_guide', '📖 Guide utilisateur / Admin'),
        ('handover', '🤝 Dossier de remise client (DOE)'),
        ('maintenance_guide', '🔧 Guide de maintenance'),
        # Autre
        ('other', '📄 Autre'),
    ], string='Type de document', required=True, default='config_switch', tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('review', 'En révision'),
        ('approved', 'Approuvé'),
        ('obsolete', 'Obsolète'),
    ], string='Statut', default='draft', tracking=True)

    version = fields.Char(string='Version', default='1.0')
    revision_date = fields.Date(string='Dernière révision')

    # ─── Contenu ───────────────────────────────────────────────────────────────
    description = fields.Html(string='Description / Résumé')
    content = fields.Html(
        string='Contenu principal',
        help='Corps du document : tableaux, configurations, explications'
    )
    raw_config = fields.Text(
        string='Configuration brute (CLI)',
        help='Coller ici la configuration CLI complète (Cisco IOS, etc.)'
    )

    # ─── Pièces jointes ────────────────────────────────────────────────────────
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'nqm_document_attachment_rel',
        'document_id',
        'attachment_id',
        string='Fichiers joints',
        help='Schémas Visio, captures Wireshark, exports Packet Tracer, etc.'
    )
    attachment_count = fields.Integer(
        compute='_compute_attachment_count', string='Fichiers'
    )

    # ─── Responsables ──────────────────────────────────────────────────────────
    author_id = fields.Many2one(
        'res.users', string='Auteur', default=lambda self: self.env.user
    )
    reviewer_id = fields.Many2one('res.users', string='Réviseur')
    approver_id = fields.Many2one('res.users', string='Approbateur')
    date_approved = fields.Date(string='Date d\'approbation')

    # ─── Équipement lié ────────────────────────────────────────────────────────
    equipment_id = fields.Many2one(
        'nqm.network.equipment', string='Équipement concerné',
        domain="[('project_id', '=', project_id)]"
    )

    tag_ids = fields.Many2many(
        'nqm.tag', 'nqm_document_tag_rel', 'document_id', 'tag_id',
        string='Tags'
    )
    confidentiality = fields.Selection([
        ('public', 'Public'),
        ('internal', 'Interne'),
        ('confidential', 'Confidentiel'),
        ('secret', 'Secret'),
    ], string='Confidentialité', default='internal')

    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'Nouveau') == 'Nouveau':
                vals['ref'] = self.env['ir.sequence'].next_by_code('nqm.document') or 'DOC-0000'
        return super().create(vals_list)

    def action_submit_review(self):
        self.state = 'review'

    def action_approve(self):
        self.state = 'approved'
        self.date_approved = fields.Date.today()
        self.approver_id = self.env.user

    def action_obsolete(self):
        self.state = 'obsolete'

    def action_reset_draft(self):
        self.state = 'draft'

    def action_get_attachment_tree_view(self):
        return {
            'name': 'Fichiers joints',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_new_version(self):
        """Crée une nouvelle version du document."""
        try:
            version_num = float(self.version or '1.0') + 0.1
            new_version = f"{version_num:.1f}"
        except ValueError:
            new_version = '1.1'

        new_doc = self.copy({
            'name': self.name,
            'version': new_version,
            'state': 'draft',
            'date_approved': False,
            'approver_id': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'nqm.document',
            'res_id': new_doc.id,
            'view_mode': 'form',
        }
