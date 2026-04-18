# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NqmAudit(models.Model):
    _name = 'nqm.audit'
    _description = 'Audit réseau & cybersécurité'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_audit desc'

    name = fields.Char(string='Titre de l\'audit', required=True, tracking=True)
    ref = fields.Char(string='Référence', readonly=True, default='Nouveau', copy=False)
    project_id = fields.Many2one(
        'nqm.network.project', string='Projet', required=True, tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner', string='Client', related='project_id.partner_id', store=True
    )

    audit_type = fields.Selection([
        ('network', '🌐 Audit réseau (architecture, flux, VLAN)'),
        ('security', '🔒 Audit de sécurité (hardening, vulnérabilités)'),
        ('compliance', '📜 Audit de conformité (ISO27001, RGPD, NIS2)'),
        ('pre_deploy', '🔍 Audit pré-déploiement'),
        ('post_deploy', '✅ Audit post-déploiement'),
        ('pentest_light', '⚠️ Revue de sécurité / Pentest léger'),
        ('soc_readiness', '🏢 Audit SOC Readiness'),
    ], string='Type d\'audit', required=True, default='network', tracking=True)

    state = fields.Selection([
        ('planned', 'Planifié'),
        ('in_progress', 'En cours'),
        ('review', 'En révision'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='planned', tracking=True)

    # ─── Dates & Responsables ──────────────────────────────────────────────────
    date_audit = fields.Date(string='Date de l\'audit', required=True)
    auditor_id = fields.Many2one(
        'res.users', string='Auditeur', default=lambda self: self.env.user
    )
    reviewer_id = fields.Many2one('res.users', string='Réviseur du rapport')

    # ─── Périmètre ─────────────────────────────────────────────────────────────
    scope = fields.Html(
        string='Périmètre audité',
        help='Quels équipements, réseaux, services sont dans le scope ?'
    )
    methodology = fields.Html(
        string='Méthodologie',
        help='Outils utilisés, approche (Nmap, Wireshark, Nessus, manuel...)'
    )

    # ─── Résultats ─────────────────────────────────────────────────────────────
    finding_ids = fields.One2many(
        'nqm.audit.finding', 'audit_id', string='Constats'
    )

    executive_summary = fields.Html(
        string='Résumé exécutif',
        help='Synthèse en langage clair pour le management'
    )
    technical_summary = fields.Html(
        string='Résumé technique',
        help='Synthèse pour les équipes techniques'
    )
    recommendations = fields.Html(string='Recommandations globales')

    # ─── Score global ──────────────────────────────────────────────────────────
    score = fields.Float(
        string='Score de sécurité (/100)',
        compute='_compute_score', store=True,
        help='Score calculé selon la criticité des constats'
    )
    score_label = fields.Char(compute='_compute_score_label', string='Niveau')

    # ─── Statistiques ──────────────────────────────────────────────────────────
    finding_critical = fields.Integer(compute='_compute_finding_stats', string='Critiques', store=True)
    finding_high = fields.Integer(compute='_compute_finding_stats', string='Élevés', store=True)
    finding_medium = fields.Integer(compute='_compute_finding_stats', string='Moyens', store=True)
    finding_low = fields.Integer(compute='_compute_finding_stats', string='Faibles', store=True)
    finding_info = fields.Integer(compute='_compute_finding_stats', string='Informatifs', store=True)
    finding_total = fields.Integer(compute='_compute_finding_stats', string='Total', store=True)
    finding_closed = fields.Integer(compute='_compute_finding_stats', string='Résolus', store=True)

    @api.depends('finding_ids.severity', 'finding_ids.state')
    def _compute_finding_stats(self):
        for rec in self:
            findings = rec.finding_ids
            rec.finding_total = len(findings)
            rec.finding_critical = len(findings.filtered(lambda f: f.severity == 'critical'))
            rec.finding_high = len(findings.filtered(lambda f: f.severity == 'high'))
            rec.finding_medium = len(findings.filtered(lambda f: f.severity == 'medium'))
            rec.finding_low = len(findings.filtered(lambda f: f.severity == 'low'))
            rec.finding_info = len(findings.filtered(lambda f: f.severity == 'info'))
            rec.finding_closed = len(findings.filtered(lambda f: f.state == 'closed'))

    @api.depends('finding_ids.severity', 'finding_ids.state')
    def _compute_score(self):
        """Score simplifié : déduction par constat non résolu selon criticité."""
        weights = {'critical': 20, 'high': 10, 'medium': 5, 'low': 2, 'info': 0}
        for rec in self:
            score = 100.0
            for finding in rec.finding_ids.filtered(lambda f: f.state != 'closed'):
                score -= weights.get(finding.severity, 0)
            rec.score = max(0.0, score)

    @api.depends('score')
    def _compute_score_label(self):
        for rec in self:
            if rec.score >= 90:
                rec.score_label = '🟢 Excellent'
            elif rec.score >= 75:
                rec.score_label = '🟡 Bon'
            elif rec.score >= 50:
                rec.score_label = '🟠 Moyen'
            elif rec.score >= 25:
                rec.score_label = '🔴 Faible'
            else:
                rec.score_label = '🚨 Critique'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'Nouveau') == 'Nouveau':
                vals['ref'] = self.env['ir.sequence'].next_by_code('nqm.audit') or 'AUD-0000'
        return super().create(vals_list)

    def action_start(self):
        self.state = 'in_progress'

    def action_review(self):
        self.state = 'review'

    def action_complete(self):
        self.state = 'completed'

    def action_cancel(self):
        self.state = 'cancelled'


class NqmAuditFinding(models.Model):
    _name = 'nqm.audit.finding'
    _description = 'Constat d\'audit réseau/sécurité'
    _order = 'severity, name'

    audit_id = fields.Many2one(
        'nqm.audit', string='Audit', required=True, ondelete='cascade'
    )
    name = fields.Char(string='Titre du constat', required=True)
    ref = fields.Char(string='Ref', compute='_compute_ref')

    severity = fields.Selection([
        ('critical', '🚨 Critique'),
        ('high', '🔴 Élevé'),
        ('medium', '🟠 Moyen'),
        ('low', '🟡 Faible'),
        ('info', '🔵 Informatif'),
    ], string='Criticité', required=True, default='medium')

    category = fields.Selection([
        ('access_control', 'Contrôle d\'accès'),
        ('authentication', 'Authentification / Mots de passe'),
        ('encryption', 'Chiffrement'),
        ('patch', 'Mises à jour / Patchs'),
        ('configuration', 'Mauvaise configuration'),
        ('network_exposure', 'Exposition réseau'),
        ('vlan_leak', 'Fuite VLAN / Isolation'),
        ('logging', 'Journalisation / Monitoring'),
        ('physical', 'Sécurité physique'),
        ('policy', 'Politique / Procédure manquante'),
        ('other', 'Autre'),
    ], string='Catégorie', default='configuration')

    state = fields.Selection([
        ('open', 'Ouvert'),
        ('in_remediation', 'En cours de correction'),
        ('closed', 'Résolu'),
        ('accepted', 'Risque accepté'),
    ], string='Statut', default='open')

    description = fields.Html(
        string='Description',
        help='Détail du constat : qu\'est-ce qui a été observé ?'
    )
    evidence = fields.Text(
        string='Preuve / Evidence',
        help='Commandes, captures, logs qui prouvent le constat'
    )
    impact = fields.Html(
        string='Impact',
        help='Quelles sont les conséquences potentielles ?'
    )
    recommendation = fields.Html(
        string='Recommandation',
        help='Comment corriger ce problème ?'
    )
    remediation_notes = fields.Text(string='Notes de remédiation')
    date_remediation = fields.Date(string='Date de correction prévue')
    date_closed = fields.Date(string='Date de résolution')
    assigned_to = fields.Many2one('res.users', string='Assigné à')

    cve_ref = fields.Char(string='Référence CVE', help='Ex: CVE-2023-12345')
    mitre_ref = fields.Char(string='MITRE ATT&CK', help='Ex: T1078 - Valid Accounts')

    @api.depends('audit_id.ref')
    def _compute_ref(self):
        for rec in self:
            rec.ref = f"{rec.audit_id.ref}-F{rec.id:03d}" if rec.audit_id else ''
