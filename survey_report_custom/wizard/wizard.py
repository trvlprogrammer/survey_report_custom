from odoo import models, api, fields, _
import xlwt
import xlsxwriter
import base64
import datetime
from odoo.exceptions import UserError, ValidationError
import os

class wizardSurveyReport(models.TransientModel):
    
    _name = "wizard.survey.report"
    
    excel_file = fields.Binary('excel file')

    file_name = fields.Char('Excel File', size=64)
    
    
    def get_report(self):
        
        get_param = self.env['ir.config_parameter'].sudo().get_param   
        file_store = get_param('file_store')
        
        #get selected active ids
        active_ids = tuple(self._context["active_ids"])
        
        #query to check how many survey is selected
        query_check_survey_count = """
            SELECT COUNT(*) as data_count FROM (
                SELECT survey_id FROM survey_user_input    
                WHERE id in %s
                GROUP BY survey_id
            )x
    
        """
        self.env.cr.execute(query_check_survey_count, ((active_ids,)),)
        data_survey = self._cr.dictfetchone()
        
        # check if user try to export more than one survey it will return error message
        if data_survey["data_count"] > 1:
            raise UserError(_('You can not export more than one survey at one time'))
        
        #query to get survey name
        query_survey = """
            SELECT ss.title AS survey_title, ss.id AS survey_id FROM survey_user_input sui
            JOIN survey_survey ss ON sui.survey_id = ss.id
            WHERE sui.id IN %s
            GROUP BY ss.title, ss.id        
        """
        self.env.cr.execute(query_survey, ((active_ids,)),)       
        survey_data = self._cr.dictfetchone()
        
        #query to get question name
        query_question = """
            SELECT ss.title AS survey_title, ss.id AS survey_id, page.id AS page_id, page.title AS page_name, sq.id AS question_id, sq.title AS question_title FROM survey_user_input sui
            JOIN survey_survey ss ON sui.survey_id = ss.id
            JOIN survey_question sq ON ss.id = sq.survey_id
            JOIN survey_question page ON sq.page_id = page.id
            WHERE sui.id IN %s
            GROUP BY ss.title, ss.id, page.id, page.title, sq.id, sq.title
            ORDER BY sq.id
        """
        
        self.env.cr.execute(query_question, ((active_ids,)),)       
        question_data = self._cr.dictfetchall()
        
        #query to get question page 
        query_page = """
            SELECT COUNT(x.page_id) AS question_amount, x.page_id, x.page_name
            FROM (
            SELECT ss.title AS survey_title, ss.id AS survey_id, page.id AS page_id, page.title AS page_name, sq.id AS question_id, sq.title AS question_title FROM survey_user_input sui
            JOIN survey_survey ss ON sui.survey_id = ss.id
            JOIN survey_question sq ON ss.id = sq.survey_id
            JOIN survey_question page ON sq.page_id = page.id
            WHERE sui.id IN %s
            GROUP BY ss.title, ss.id, page.id, page.title, sq.id, sq.title
            )x GROUP BY x.page_id, x.page_name        
        """
        
        self.env.cr.execute(query_page, ((active_ids,)),)       
        page_data = self._cr.dictfetchall()
        
        # query get user answer
        query = """        
            SELECT x.question_title, x.page_name, x.question_id, x.page_id, x.survey_title, x.user_name, x.survey_date, x.user_input_id, STRING_AGG (answer, ', ') answer, x.user_input_id
            FROM(
            SELECT question.question_title, question.page_name, question.question_id, question.page_id, ss.title AS survey_title, rp.name AS user_name, CAST(sui.create_date AS VARCHAR) AS survey_date,
            CASE 
                WHEN suil.answer_type = 'text_box' THEN suil.value_text_box
                WHEN suil.answer_type = 'char_box' THEN suil.value_char_box
                WHEN suil.answer_type = 'numerical_box' THEN CAST(suil.value_numerical_box AS VARCHAR)
                WHEN suil.answer_type = 'date' THEN CAST(suil.value_date AS VARCHAR) 
                WHEN suil.answer_type = 'datetime' THEN CAST(suil.value_datetime AS VARCHAR)  
                WHEN suil.answer_type = 'suggestion' THEN CAST(sqa.value AS VARCHAR) 
                ELSE ''
            END AS answer,
            suil.id AS answer_line_id, sui.id AS user_input_id
            FROM survey_user_input_line suil       
            JOIN survey_user_input sui ON suil.user_input_id = sui.id
            LEFT JOIN (
                SELECT sq.title AS question_title, sq2.title AS page_name, sq.id AS question_id, sq2.id AS page_id FROM survey_question sq
                JOIN survey_question sq2 ON sq.page_id = sq2.id ORDER BY sq.page_id
            )AS question ON suil.question_id = question.question_id
            JOIN survey_survey ss ON suil.survey_id = ss.id
            LEFT JOIN res_partner rp on sui.partner_id = rp.id 
            LEFT JOIN survey_question_answer sqa on suil.suggested_answer_id = sqa.id
            )x
            WHERE x.user_input_id in %s 
            GROUP BY x.question_title, x.page_name, x.question_id, x.page_id, x.survey_title, x.user_name, x.survey_date, x.user_input_id
            ORDER BY x.user_input_id, x.page_id                    
        """
                
        self.env.cr.execute(query, ((active_ids,)),)       
        data = self._cr.dictfetchall()
        
        ############################set the data###########################
        input_ids = []
        user_data = []
                
        for d in data :        
            if d["user_input_id"] not in input_ids:
                input_ids.append(d["user_input_id"])
                user_data.append({
                    "user_input_id" : d["user_input_id"],
                    "user_name" : d["user_name"],            
                    "survey_date" : d["survey_date"],
                    "answer_data" : [
                        {
                        "question_id" :d["question_id"],
                         "answer" : d["answer"]
                        }
                    ]
                })
            else :
                for user_d in user_data:
                    if d["user_input_id"] == user_d["user_input_id"]:
                        user_d["answer_data"].append(
                            {
                                "question_id" :d["question_id"],
                                "answer" : d["answer"]
                            }   
                        )
                        
        #####################################################################
        
        ######################Processing generate xls file###################
                        
        now = datetime.datetime.now()
        date = now.strftime("%d_%m_%Y_%H_%M_%S")
        file_name = f"survey_report_{str(date)}.xlsx"
        path_file = os.path.join(file_store,file_name)
        
        workbook = xlsxwriter.Workbook(path_file)
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format({'bold': 1})
        worksheet.merge_range('A1:F3', survey_data["survey_title"],bold)
        worksheet.write("A6", "#")
        
        worksheet.set_column('B4:B5', 28)
        worksheet.merge_range('B4:B5', 'Survey_date',bold)
        
        worksheet.set_column('C4:C5', 28)
        worksheet.merge_range('C4:C5', 'User',bold)
        
        
        start_cell = "D"
        data_cell_page = []
        for page in page_data:
            next_cell = chr(ord(start_cell) + page["question_amount"]-1)    
            worksheet.merge_range(f'{start_cell}4:{next_cell}5', page["page_name"],bold) 
            
            data_cell_page.append({
                "page_id" : page["page_id"],
                "start_cell" : f"{start_cell}",
                "end_cell" : f"{next_cell}",
                "row_cell": 5
            })
            start_cell = chr(ord(start_cell) + page["question_amount"])

        data_next_cell = {}
        question_cell_data = []
        for question in question_data:
            if str(question["page_id"]) not in data_next_cell:
                for cell_page in data_cell_page:
                    if cell_page["page_id"] == question["page_id"]:                
                        cell = f"{cell_page['start_cell']}6"
                        worksheet.set_column(f"{cell}:{cell}", 28)
                        worksheet.write( cell, question["question_title"])
                        data_next_cell[str(question["page_id"])] = chr(ord(cell_page['start_cell']) + 1) 
                        question_cell_data.append({
                            "question_id" : question["question_id"],
                            "start_row" : 6,
                            "cell" : cell_page['start_cell']
                        })
            else :
                next_cell = str(question["page_id"])
                cell = f"{data_next_cell[next_cell]}6"
                worksheet.set_column(f"{cell}:{cell}", 28)
                worksheet.write( cell, question["question_title"])
                
                question_cell_data.append({
                                "question_id" : question["question_id"],
                                "start_row" : 6,
                                "cell" : data_next_cell[next_cell]
                            }) 
                data_next_cell[str(question["page_id"])] = chr(ord(data_next_cell[next_cell]) + 1)
            
            
        user_next_row = 7
        number = 1
        for user in user_data:
            row = str(user_next_row)
            worksheet.write( f"A{row}", number)
            worksheet.write( f"B{row}", user["survey_date"])
            worksheet.write( f"C{row}", user["user_name"])
        
            for ans in user["answer_data"]:
                for q in question_cell_data :
                    if ans["question_id"] == q["question_id"]:
                        cell = q['cell'] + row
                        worksheet.write( cell, ans["answer"])
        
            user_next_row += 1
            number += 1
        
                
        
        workbook.close()
        
        #####################################################################
        
        # open file and save as binary in wizard model
        with open(path_file, "rb") as file:
            file_base64 = base64.b64encode(file.read())
            
        self.file_name = file_name
        self.excel_file = file_base64
        
        return {
                'view_mode': 'form',
                'res_id': self.id,
                'res_model': 'wizard.survey.report',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'target': 'new',
              }