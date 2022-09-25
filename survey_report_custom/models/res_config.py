from odoo import api, fields, models


# configuration for report
class res_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    file_store = fields.Char(string='File Store')
    
    def set_values(self):
        super(res_config_settings, self).set_values()
        set_param = self.env['ir.config_parameter'].set_param
        set_param('file_store', (self.file_store or ''))
        
    @api.model
    def get_values(self):
        
        res = super(res_config_settings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param                
        res.update(file_store=get_param('file_store', default=''))        
        return res