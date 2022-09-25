# -*- coding: utf-8 -*-
{
    'name': "Survey Report Custom",

    'summary': """
        Survey Report Custom""",
                
    'description': """
        Survey Report Custom
    """,
    
    'author': "Alfatih Ridho NT",
    'website': "alfatihridhont@gmail.com",
    'category': 'Survey',
    'version': '15.0.1',
    'depends': ['base','survey'],    
    'data': [
        'wizard/wizard.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings.xml'
    ],
    
}
