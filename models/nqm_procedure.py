# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NqmProcedureCategory(models.Model):
    _name = 'nqm.procedure.category'
    _description = 'Catégorie de procédure réseau'
    _order = 'name'

    name = fields.Char(string='Catégorie', required=True)
    code = fields.Char(string='Code')
    color = fields.Integer(string='Couleur')
    description = fields.Text(string='Description')
    procedure_count = fields.Integer(
        compute='_compute_procedure_count', string='Procédures'
    )

    def _compute_procedure_count(self):
        for rec in self:
            rec.procedure_count = self.env['nqm.procedure'].search_count(
                [('category_id', '=', rec.id)]
            )


class NqmProcedure(models.Model):
    _name = 'nqm.procedure'
    _description = 'Procédure technique réseau/cybersécurité'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'category_id, name'

    # ─── Identification ────────────────────────────────────────────────────────
    name = fields.Char(string='Titre de la procédure', required=True, tracking=True)
    ref = fields.Char(string='Référence', readonly=True, default='Nouveau', copy=False)
    category_id = fields.Many2one(
        'nqm.procedure.category', string='Catégorie', required=True
    )
    project_id = fields.Many2one(
        'nqm.network.project', string='Projet', tracking=True,
        help='Laisser vide pour une procédure de bibliothèque (réutilisable)'
    )
    partner_id = fields.Many2one(
        'res.partner', string='Client', related='project_id.partner_id', store=True
    )

    # ─── Classification ────────────────────────────────────────────────────────
    procedure_type = fields.Selection([
        ('installation', 'Installation / Câblage'),
        ('configuration', 'Configuration équipement'),
        ('vlan', 'Gestion VLAN / Segmentation'),
        ('routing', 'Configuration routage'),
        ('security', 'Durcissement / Sécurité'),
        ('backup', 'Sauvegarde de configuration'),
        ('monitoring', 'Supervision / Monitoring'),
        ('incident', 'Réponse à incident'),
        ('maintenance', 'Maintenance'),
        ('other', 'Autre'),
    ], string='Type de procédure', required=True, default='configuration')

    is_template = fields.Boolean(
        string='Modèle réutilisable',
        help='Si coché, cette procédure est une template de bibliothèque'
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('review', 'En révision'),
        ('approved', 'Approuvé'),
        ('obsolete', 'Obsolète'),
    ], string='Statut', default='draft', tracking=True)

    version = fields.Char(string='Version', default='1.0')
    revision_date = fields.Date(string='Date de révision')

    # ─── Contenu ───────────────────────────────────────────────────────────────
    objective = fields.Text(
        string='Objectif',
        help='En une phrase, quel est le but de cette procédure ?'
    )
    prerequisites = fields.Html(
        string='Prérequis',
        help='Matériel, accès, connaissances nécessaires avant de commencer'
    )
    steps = fields.Html(
        string='Étapes de la procédure',
        help='Détail pas-à-pas des opérations à réaliser'
    )
    commands = fields.Text(
        string='Commandes CLI / Scripts',
        help='Bloc de commandes Cisco IOS, bash, PowerShell, etc.'
    )
    expected_result = fields.Html(
        string='Résultat attendu',
        help='Comment vérifier que la procédure a bien été appliquée ?'
    )
    risks = fields.Html(
        string='Risques & Points d\'attention',
        help='Ce qui peut mal tourner et comment l\'éviter'
    )
    rollback = fields.Html(
        string='Procédure de rollback',
        help='Comment revenir en arrière si quelque chose se passe mal ?'
    )
    references = fields.Text(
        string='Références',
        help='Liens vers documentation Cisco, RFC, CVE, etc.'
    )

    # ─── Responsables ──────────────────────────────────────────────────────────
    author_id = fields.Many2one(
        'res.users', string='Auteur',
        default=lambda self: self.env.user
    )
    reviewer_id = fields.Many2one('res.users', string='Réviseur')
    approver_id = fields.Many2one('res.users', string='Approbateur')
    date_approved = fields.Date(string='Date d\'approbation')

    # ─── Tags ──────────────────────────────────────────────────────────────────
    tag_ids = fields.Many2many(
        'nqm.tag', 'nqm_procedure_tag_rel', 'procedure_id', 'tag_id',
        string='Tags'
    )

    # ─── Estimation ────────────────────────────────────────────────────────────
    estimated_duration = fields.Float(
        string='Durée estimée (h)',
        help='Temps nécessaire pour exécuter cette procédure'
    )
    skill_level = fields.Selection([
        ('junior', 'Junior (< 1 an)'),
        ('intermediate', 'Intermédiaire (1-3 ans)'),
        ('senior', 'Senior (3+ ans)'),
    ], string='Niveau requis', default='intermediate')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'Nouveau') == 'Nouveau':
                vals['ref'] = self.env['ir.sequence'].next_by_code('nqm.procedure') or 'PROC-0000'
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

    def action_copy_to_project(self):
        """Dupliquer cette procédure template vers un projet."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Copier vers un projet',
            'res_model': 'nqm.procedure',
            'view_mode': 'form',
            'context': {
                'default_name': self.name + ' (copie)',
                'default_category_id': self.category_id.id,
                'default_procedure_type': self.procedure_type,
                'default_objective': self.objective,
                'default_steps': self.steps,
                'default_commands': self.commands,
                'default_expected_result': self.expected_result,
                'default_is_template': False,
            },
        }


class NqmTag(models.Model):
    _name = 'nqm.tag'
    _description = 'Tag réseau/cybersécurité'
    _order = 'name'

    name = fields.Char(string='Tag', required=True)
    color = fields.Integer(string='Couleur')
