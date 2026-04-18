# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NqmChecklist(models.Model):
    _name = 'nqm.checklist'
    _description = 'Checklist de projet réseau'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, phase, name'

    name = fields.Char(string='Titre de la checklist', required=True, tracking=True)
    ref = fields.Char(string='Référence', readonly=True, default='Nouveau', copy=False)
    project_id = fields.Many2one(
        'nqm.network.project', string='Projet', required=True, tracking=True
    )
    phase = fields.Selection([
        ('pre_design', 'Pré-conception / Recueil des besoins'),
        ('design', 'Conception & Architecture'),
        ('pre_deploy', 'Pré-déploiement'),
        ('deploy', 'Déploiement'),
        ('test', 'Tests & Validation'),
        ('commissioning', 'Commissioning / Mise en service'),
        ('handover', 'Remise au client / Formation'),
        ('audit', 'Audit de sécurité'),
    ], string='Phase', required=True, default='design')

    is_template = fields.Boolean(string='Modèle réutilisable')
    state = fields.Selection([
        ('open', 'En cours'),
        ('done', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='open', tracking=True)

    assigned_to = fields.Many2one('res.users', string='Assigné à')
    due_date = fields.Date(string='Date limite')
    notes = fields.Html(string='Notes / Contexte')

    item_ids = fields.One2many(
        'nqm.checklist.item', 'checklist_id', string='Éléments'
    )

    # ─── Statistiques ──────────────────────────────────────────────────────────
    total_items = fields.Integer(compute='_compute_stats', string='Total items', store=True)
    done_items = fields.Integer(compute='_compute_stats', string='Faits', store=True)
    completion_rate = fields.Float(compute='_compute_stats', string='Avancement (%)', store=True)

    @api.depends('item_ids.state')
    def _compute_stats(self):
        for rec in self:
            items = rec.item_ids
            rec.total_items = len(items)
            rec.done_items = len(items.filtered(lambda i: i.state == 'done'))
            rec.completion_rate = (rec.done_items / rec.total_items * 100) if rec.total_items else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'Nouveau') == 'Nouveau':
                vals['ref'] = self.env['ir.sequence'].next_by_code('nqm.checklist') or 'CHK-0000'
        return super().create(vals_list)

    def action_mark_done(self):
        self.item_ids.filtered(lambda i: i.state != 'na').write({'state': 'done'})
        self.state = 'done'

    def action_reopen(self):
        self.state = 'open'


class NqmChecklistItem(models.Model):
    _name = 'nqm.checklist.item'
    _description = 'Élément de checklist réseau'
    _order = 'sequence, id'

    checklist_id = fields.Many2one(
        'nqm.checklist', string='Checklist', required=True, ondelete='cascade'
    )
    sequence = fields.Integer(string='Ordre', default=10)
    name = fields.Char(string='Point de contrôle', required=True)
    description = fields.Text(string='Description / Critère de validation')
    category = fields.Selection([
        ('physical', 'Physique / Câblage'),
        ('ip', 'Adressage IP / VLAN'),
        ('routing', 'Routage'),
        ('security', 'Sécurité / Hardening'),
        ('test', 'Test de connectivité'),
        ('doc', 'Documentation'),
        ('handover', 'Remise client'),
        ('other', 'Autre'),
    ], string='Catégorie', default='other')

    state = fields.Selection([
        ('todo', 'À faire'),
        ('in_progress', 'En cours'),
        ('done', 'OK'),
        ('failed', 'Échoué'),
        ('na', 'N/A'),
    ], string='Statut', default='todo')

    is_critical = fields.Boolean(
        string='Critique',
        help='Si coché, ce point bloque la validation de la phase'
    )
    assigned_to = fields.Many2one('res.users', string='Responsable')
    done_date = fields.Datetime(string='Date de réalisation')
    notes = fields.Text(string='Remarques / Preuves')
    evidence_attachment = fields.Binary(string='Capture / Preuve')
    evidence_filename = fields.Char(string='Nom du fichier')

    @api.onchange('state')
    def _onchange_state(self):
        if self.state == 'done':
            self.done_date = fields.Datetime.now()
            self.assigned_to = self.env.user
