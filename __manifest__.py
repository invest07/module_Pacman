# -*- coding: utf-8 -*-
{
    'name': 'Network Quality Management',
    'version': '16.0.1.0.0',
    'category': 'Technical',
    'summary': 'Gestion complète des projets réseau & cybersécurité : procédures, checklists, audits, commissioning, documents de configuration et validation.',
    'description': """
Network Quality Management
==========================
Module de gestion de la qualité pour les projets d'architecture réseau et cybersécurité.

Fonctionnalités :
- Projets réseau liés aux clients
- Bibliothèque de procédures techniques réutilisables
- Checklists par phase (conception, déploiement, validation, livraison)
- Documents de configuration (plans IP, configs Cisco, diagrammes)
- Fiches de test & validation avec statut
- Audits réseau/sécurité avec scoring
- Commissioning avec PV de mise en service
- Tableau de bord qualité
    """,
    'author': 'WorkFlowImpact AI',
    'website': 'https://workflowimpact.ai',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'project',
        'maintenance',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/nqm_sequence_data.xml',
        'data/nqm_procedure_category_data.xml',
        'views/nqm_project_views.xml',
        'views/nqm_procedure_views.xml',
        'views/nqm_checklist_views.xml',
        'views/nqm_document_views.xml',
        'views/nqm_audit_views.xml',
        'views/nqm_commissioning_views.xml',
        'views/nqm_menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [],
}
