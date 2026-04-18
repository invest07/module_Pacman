# -*- coding: utf-8 -*-
from odoo import models, fields, api


class NqmCommissioning(models.Model):
    _name = 'nqm.commissioning'
    _description = 'Commissioning / Procès-verbal de mise en service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_commissioning desc'

    name = fields.Char(
        string='Titre du commissioning', required=True, tracking=True,
        help='Ex: Mise en service VLAN Infrastructure - Site Ciney'
    )
    ref = fields.Char(string='Référence PV', readonly=True, default='Nouveau', copy=False)
    project_id = fields.Many2one(
        'nqm.network.project', string='Projet', required=True, tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner', string='Client', related='project_id.partner_id', store=True
    )

    commissioning_type = fields.Selection([
        ('partial', 'Mise en service partielle (périmètre limité)'),
        ('full', 'Mise en service complète'),
        ('handover', 'Remise officielle au client'),
        ('acceptance', 'Réception & Acceptation client'),
    ], string='Type', required=True, default='full', tracking=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('scheduled', 'Planifié'),
        ('in_progress', 'En cours'),
        ('pending_signature', 'En attente de signature'),
        ('signed', 'Signé / Validé'),
        ('cancelled', 'Annulé'),
    ], string='Statut', default='draft', tracking=True)

    # ─── Dates ─────────────────────────────────────────────────────────────────
    date_commissioning = fields.Datetime(
        string='Date & heure de mise en service', required=True
    )
    date_signed = fields.Datetime(string='Date de signature', tracking=True)

    # ─── Participants ──────────────────────────────────────────────────────────
    technician_id = fields.Many2one(
        'res.users', string='Technicien / Ingénieur',
        default=lambda self: self.env.user
    )
    client_contact = fields.Char(
        string='Représentant client',
        help='Nom et fonction du représentant du client présent'
    )
    witnesses = fields.Text(
        string='Autres participants',
        help='Liste des autres personnes présentes lors du commissioning'
    )

    # ─── Périmètre & Résumé ────────────────────────────────────────────────────
    scope_description = fields.Html(
        string='Périmètre de la mise en service',
        help='Quels équipements, services, VLANs sont mis en service ?'
    )
    pre_conditions = fields.Html(
        string='Conditions préalables vérifiées',
        help='Vérifications effectuées AVANT la mise en service'
    )

    # ─── Tests de réception ────────────────────────────────────────────────────
    test_ids = fields.One2many(
        'nqm.commissioning.test', 'commissioning_id',
        string='Tests de réception'
    )

    # ─── Résultat global ───────────────────────────────────────────────────────
    overall_result = fields.Selection([
        ('pass', '✅ Réussi - Mise en service validée'),
        ('pass_with_reserves', '⚠️ Réussi avec réserves'),
        ('fail', '❌ Échoué - Corrections requises'),
        ('pending', '⏳ En attente de résolution'),
    ], string='Résultat global', tracking=True)

    reserves = fields.Html(
        string='Réserves / Non-conformités',
        help='Points à corriger ou à surveiller après la mise en service'
    )
    observations = fields.Html(
        string='Observations générales',
        help='Remarques libres sur le déroulement de la mise en service'
    )
    corrective_actions = fields.Html(
        string='Actions correctives planifiées',
        help='Pour les réserves : qui fait quoi et pour quand ?'
    )

    # ─── Signature & Validation ────────────────────────────────────────────────
    client_signature = fields.Binary(string='Signature client')
    technician_signature = fields.Binary(string='Signature technicien')
    signature_place = fields.Char(string='Lieu de signature')
    client_approval = fields.Boolean(
        string='Approuvé par le client', tracking=True
    )
    notes_signature = fields.Text(
        string='Commentaires lors de la signature'
    )

    # ─── Documents liés ────────────────────────────────────────────────────────
    checklist_ids = fields.Many2many(
        'nqm.checklist',
        'nqm_commissioning_checklist_rel',
        'commissioning_id', 'checklist_id',
        string='Checklists associées',
        domain="[('project_id', '=', project_id)]"
    )
    document_ids = fields.Many2many(
        'nqm.document',
        'nqm_commissioning_doc_rel',
        'commissioning_id', 'document_id',
        string='Documents remis au client',
        domain="[('project_id', '=', project_id)]"
    )

    # ─── Stats ─────────────────────────────────────────────────────────────────
    test_total = fields.Integer(compute='_compute_test_stats', string='Tests total', store=True)
    test_passed = fields.Integer(compute='_compute_test_stats', string='Réussis', store=True)
    test_failed = fields.Integer(compute='_compute_test_stats', string='Échoués', store=True)
    test_rate = fields.Float(compute='_compute_test_stats', string='Taux de réussite (%)', store=True)

    @api.depends('test_ids.result')
    def _compute_test_stats(self):
        for rec in self:
            tests = rec.test_ids
            rec.test_total = len(tests)
            rec.test_passed = len(tests.filtered(lambda t: t.result == 'pass'))
            rec.test_failed = len(tests.filtered(lambda t: t.result == 'fail'))
            rec.test_rate = (rec.test_passed / rec.test_total * 100) if rec.test_total else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'Nouveau') == 'Nouveau':
                vals['ref'] = self.env['ir.sequence'].next_by_code('nqm.commissioning') or 'COM-0000'
        return super().create(vals_list)

    def action_schedule(self):
        self.state = 'scheduled'

    def action_start(self):
        self.state = 'in_progress'

    def action_pending_signature(self):
        self.state = 'pending_signature'

    def action_sign(self):
        self.state = 'signed'
        self.date_signed = fields.Datetime.now()

    def action_cancel(self):
        self.state = 'cancelled'


class NqmCommissioningTest(models.Model):
    _name = 'nqm.commissioning.test'
    _description = 'Test de réception pour commissioning'
    _order = 'sequence, id'

    commissioning_id = fields.Many2one(
        'nqm.commissioning', string='Commissioning', required=True, ondelete='cascade'
    )
    sequence = fields.Integer(string='Ordre', default=10)
    name = fields.Char(string='Test', required=True)
    description = fields.Text(
        string='Procédure de test',
        help='Comment exécuter ce test ?'
    )
    test_category = fields.Selection([
        ('connectivity', '🌐 Connectivité (ping, traceroute)'),
        ('vlan_isolation', '🔀 Isolation VLAN'),
        ('routing', '🔀 Routage inter-VLAN / inter-sites'),
        ('internet', '🌍 Accès Internet'),
        ('dns', '📡 Résolution DNS'),
        ('dhcp', '📋 Attribution DHCP'),
        ('vpn', '🔐 Tunnel VPN'),
        ('firewall_rules', '🔥 Règles Firewall / ACL'),
        ('authentication', '🔑 Authentification (802.1X, etc.)'),
        ('failover', '♻️ Bascule / Haute disponibilité'),
        ('performance', '📊 Performance / Bande passante'),
        ('other', '📋 Autre'),
    ], string='Catégorie', default='connectivity')

    expected_result = fields.Text(
        string='Résultat attendu',
        help='Quel est le comportement normal attendu ?'
    )
    actual_result = fields.Text(
        string='Résultat observé',
        help='Ce qui a réellement été observé lors du test'
    )
    result = fields.Selection([
        ('pass', '✅ Réussi'),
        ('fail', '❌ Échoué'),
        ('na', 'N/A'),
        ('pending', '⏳ À tester'),
    ], string='Résultat', default='pending')

    is_critical = fields.Boolean(
        string='Test bloquant',
        help='Si ce test échoue, le commissioning est bloqué'
    )
    notes = fields.Text(string='Remarques')
    tester_id = fields.Many2one('res.users', string='Testé par')
    test_date = fields.Datetime(string='Date du test')

    @api.onchange('result')
    def _onchange_result(self):
        if self.result in ('pass', 'fail'):
            self.tester_id = self.env.user
            self.test_date = fields.Datetime.now()
