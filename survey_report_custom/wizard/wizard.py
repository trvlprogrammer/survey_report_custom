from odoo import models, api, fields, _

class wizardSurveyReport(models.TransientModel):
    
    _name = "wizard.survey.report"
    
    flaging = fields.Boolean("flaging")
    message = fields.Char(string="Message")
    
    
    def get_report(self):
        
        print("get report")