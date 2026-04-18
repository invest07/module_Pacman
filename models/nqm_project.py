# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NqmNetworkProject(models.Model):
    _name = 'nqm.network.project'
    _description = 'Projet Réseau & Cybersécurité'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    # ─── Identification ────────────────────────────────────────────────────────
    name = fields.Char(
        string='Nom du projet', required=True, tracking=True,
        help='Ex: Architecture réseau VLAN - Client Dherte SA'
    )
    ref = fields.Char(
        string='Référence', readonly=True, default='Nouveau',
        copy=False, tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner', string='Client', required=True, tracking=True
    )
    project_id = fields.Many2one(
        'project.project', string='Projet Odoo lié',
        help='Lien vers le projet Odoo standard si nécessaire'
    )

    # ─── Classification ────────────────────────────────────────────────────────
    project_type = fields.Selection([
        ('lan', 'LAN / Infrastructure locale'),
        ('wan', 'WAN / Interconnexion de sites'),
        ('vlan', 'VLAN / Segmentation réseau'),
        ('wifi', 'Wi-Fi / Réseau sans fil'),
        ('vpn', 'VPN / Tunnel sécurisé'),
        ('firewall', 'Firewall / Sécurité périmétrique'),
        ('soc', 'SOC / Surveillance & SIEM'),
        ('cloud', 'Cloud / Hybride'),
        ('full', 'Projet complet multi-domaines'),
        ('audit', 'Audit réseau / Cybersécurité'),
    ], string='Type de projet', required=True, default='lan', tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('design', 'Conception'),
        ('deploy', 'Déploiement'),
        ('test', 'Tests & Validation'),
        ('commissioning', 'Commissioning'),
        ('done', 'Livré'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', tracking=True, group_expand='_expand_states')

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Critique'),
    ], string='Priorité', default='0')

    # ─── Dates ─────────────────────────────────────────────────────────────────
    date_start = fields.Date(string='Date de début', tracking=True)
    date_end = fields.Date(string='Date de fin prévue', tracking=True)
    date_delivered = fields.Date(string='Date de livraison réelle')

    # ─── Responsables ──────────────────────────────────────────────────────────
    user_id = fields.Many2one(
        'res.users', string='Responsable projet',
        default=lambda self: self.env.user, tracking=True
    )
    engineer_ids = fields.Many2many(
        'res.users', 'nqm_project_engineer_rel',
        'project_id', 'user_id',
        string='Ingénieurs / Techniciens'
    )

    # ─── Description technique ─────────────────────────────────────────────────
    description = fields.Html(string='Description du projet')
    scope = fields.Html(
        string='Périmètre (Scope)',
        help='Définition claire de ce qui est inclus et exclu du projet'
    )
    network_topology = fields.Html(
        string='Topologie réseau',
        help='Description de la topologie : nombre de sites, équipements, schéma logique'
    )
    ip_plan = fields.Text(
        string='Plan d\'adressage IP',
        help='Tableau des plages IP, VLANs, sous-réseaux alloués'
    )

    # ─── Équipements ───────────────────────────────────────────────────────────
    equipment_ids = fields.One2many(
        'nqm.network.equipment', 'project_id',
        string='Équipements réseau'
    )

    # ─── Relations vers les autres objets ──────────────────────────────────────
    procedure_ids = fields.One2many(
        'nqm.procedure', 'project_id', string='Procédures'
    )
    checklist_ids = fields.One2many(
        'nqm.checklist', 'project_id', string='Checklists'
    )
    document_ids = fields.One2many(
        'nqm.document', 'project_id', string='Documents'
    )
    audit_ids = fields.One2many(
        'nqm.audit', 'project_id', string='Audits'
    )
    commissioning_ids = fields.One2many(
        'nqm.commissioning', 'project_id', string='Commissioning'
    )

    # ─── Compteurs (pour les boutons smart) ────────────────────────────────────
    procedure_count = fields.Integer(compute='_compute_counts', string='Procédures')
    checklist_count = fields.Integer(compute='_compute_counts', string='Checklists')
    document_count = fields.Integer(compute='_compute_counts', string='Documents')
    audit_count = fields.Integer(compute='_compute_counts', string='Audits')
    commissioning_count = fields.Integer(compute='_compute_counts', string='Commissioning')

    # ─── Taux de complétion global ─────────────────────────────────────────────
    completion_rate = fields.Float(
        string='Complétion (%)', compute='_compute_completion_rate',
        store=True, help='Taux de complétion basé sur les checklists'
    )

    @api.depends('procedure_ids', 'checklist_ids', 'document_ids', 'audit_ids', 'commissioning_ids')
    def _compute_counts(self):
        for rec in self:
            rec.procedure_count = len(rec.procedure_ids)
            rec.checklist_count = len(rec.checklist_ids)
            rec.document_count = len(rec.document_ids)
            rec.audit_count = len(rec.audit_ids)
            rec.commissioning_count = len(rec.commissioning_ids)

    @api.depends('checklist_ids.completion_rate')
    def _compute_completion_rate(self):
        for rec in self:
            checklists = rec.checklist_ids
            if checklists:
                rec.completion_rate = sum(checklists.mapped('completion_rate')) / len(checklists)
            else:
                rec.completion_rate = 0.0

    @api.model
    def _expand_states(self, states, domain, order):
        return [key for key, _ in self._fields['state'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'Nouveau') == 'Nouveau':
                vals['ref'] = self.env['ir.sequence'].next_by_code('nqm.network.project') or 'NQM-0000'
        return super().create(vals_list)

    def action_design(self):
        self.state = 'design'

    def action_deploy(self):
        self.state = 'deploy'

    def action_test(self):
        self.state = 'test'

    def action_commissioning(self):
        self.state = 'commissioning'

    def action_done(self):
        self.state = 'done'
        self.date_delivered = fields.Date.today()

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset_draft(self):
        self.state = 'draft'

    # ─── Actions boutons smart ─────────────────────────────────────────────────
    def action_view_procedures(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Procédures',
            'res_model': 'nqm.procedure',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_checklists(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Checklists',
            'res_model': 'nqm.checklist',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_documents(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'nqm.document',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_audits(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Audits',
            'res_model': 'nqm.audit',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_commissioning(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Commissioning',
            'res_model': 'nqm.commissioning',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }


class NqmNetworkEquipment(models.Model):
    _name = 'nqm.network.equipment'
    _description = 'Équipement réseau du projet'
    _order = 'equipment_type, name'

    project_id = fields.Many2one(
        'nqm.network.project', string='Projet', required=True, ondelete='cascade'
    )
    name = fields.Char(string='Nom / Hostname', required=True)
    equipment_type = fields.Selection([
        ('router', 'Routeur'),
        ('switch_l2', 'Switch L2'),
        ('switch_l3', 'Switch L3 / MLS'),
        ('firewall', 'Firewall'),
        ('ap', 'Point d\'accès Wi-Fi'),
        ('server', 'Serveur'),
        ('ids_ips', 'IDS/IPS'),
        ('siem', 'SIEM'),
        ('other', 'Autre'),
    ], string='Type', required=True, default='switch_l2')
    brand = fields.Char(string='Marque', help='Ex: Cisco, Fortinet, Palo Alto')
    model = fields.Char(string='Modèle', help='Ex: Catalyst 2960, ASA 5505')
    ip_management = fields.Char(string='IP de management')
    vlan_management = fields.Integer(string='VLAN de management')
    location = fields.Char(string='Emplacement / Baie')
    serial_number = fields.Char(string='N° de série')
    firmware_version = fields.Char(string='Version firmware/IOS')
    notes = fields.Text(string='Notes')
    config_document_id = fields.Many2one(
        'nqm.document', string='Document de config lié'
    )
