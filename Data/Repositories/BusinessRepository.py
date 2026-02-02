import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

""" Fetch from postgres repository class."""
class BusinessRepository:
    def __init__(self, db):
        logger.info("[INFO] call stack init BusinessRepository")
        self.db = db
    
    def get_district_by_id(self, params: tuple)->list:
        """ Returns an array of values """
        query = "SELECT name, city, state, region FROM " \
        "stu_tracker.District WHERE organization_id = %s AND id = %s;"
        logger.info(f"[DB] executing get_district_by_id query: {query} and with {params}")
        data = self.db.fetch_one(query, params)
        if not data:
            return None
        return dict(data)    

    def get_subjects_by_id(self, params: tuple)->list:
        """ Returns an array of values """
        query = "SELECT title, description FROM stu_tracker.Subjects " \
        "WHERE organization_id = %s AND id = %s;"
        logger.info(f"[DB] executing get_subjects_by_id query: {query} and with {params}")
        data = self.db.fetch_one(query, params)
        if not data:
            return None
        return dict(data)

    def update_aquestion_json_by_input_key(self, params: tuple) ->int:
        """ Update a Generate_questions_task given a input_key and organization_id"""
        query = "UPDATE stu_tracker.Generate_questions_task SET " \
        "json_output = %s, status = 'DONE' WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing update_aquestion_json_by_input_key query: {query} and with {params}")
        return self.db.execute_res(query, params)
    
    def update_gmaterials_json_by_input_key(self, params: tuple) ->int:
        """ Update a Generate_questions_task given a input_key and organization_id"""
        query = "UPDATE stu_tracker.Generate_materials_task SET " \
        "json_output = %s, status = 'DONE' WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing update_gmaterials_json_by_input_key query: {query} and with {params}")
        return self.db.execute_res(query, params)
    
    def update_questions_status_by_input_key(self, params: tuple) ->int:
        """ Update state of request """
        query = "UPDATE stu_tracker.Generate_questions_task SET " \
        "status = %s, retry_count = retry_count + 1 WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing update_questions_status_by_input_key query: {query} and with {params}")
        return self.db.execute_res(query, params)

    def update_materials_status_by_input_key(self, params: tuple) ->int:
        """ Update state of request """
        query = "UPDATE stu_tracker.Generate_materials_task SET " \
        "status = %s, retry_count = retry_count + 1 WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing update_materials_status_by_input_key query: {query} and with {params}")
        return self.db.execute_res(query, params)
    
    def update_materials_task_by_input_key(self, params: tuple) ->int:
        """ Update state of request """
        query = "UPDATE stu_tracker.Generate_materials_task SET " \
        "status = %s, retry_count = retry_count + 1 WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing update_materials_task_by_input_key query: {query} and with {params}")
        return self.db.execute_res(query, params)
    
    def get_status_by_input_key(self, params: tuple)->dict:
        query = "SELECT status, retry_count FROM stu_tracker.Generate_questions_task " \
        "WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing get_status_by_input_key query: {query} and with {params}")
        return self.db.fetch_one(query, params)
    

    def update_aquestion_usage_by_input_key(self, params: tuple) ->int:
        """ Update a Generate_questions_task given a input_key and organization_id"""
        query = "UPDATE stu_tracker.Generate_questions_task SET " \
        "input_tokens = %s, output_tokens = %s WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing update_aquestion_usage_by_input_key query: {query} and with {params}")
        return self.db.execute_res(query, params)
    
    def update_gmaterials_usage_by_input_key(self, params: tuple) ->int:
        """ Update a Generate_questions_task given a input_key and organization_id"""
        query = "UPDATE stu_tracker.Generate_materials_task SET " \
        "input_tokens = %s, output_tokens = %s WHERE organization_id = %s AND s3_output_key = %s;"
        logger.info(f"[DB] executing update_gmaterials_usage_by_input_key query: {query} and with {params}")
        return self.db.execute_res(query, params)
    
    def get_assessment_by_id(self, params: tuple) ->dict:
        query = "SELECT a.id, a.title AS assessment_title, a.description AS assessment_description, s.title AS subject_title, s.description AS subject_description " \
        "FROM stu_tracker.Assessments a JOIN stu_tracker.Subjects s " \
        "ON s.id = a.subject_id " \
        "WHERE a.organization_id = %s AND a.id = %s;"
        logger.info(f"[DB] executing update_gmaterials_usage_by_input_key query: {query} and with {params}")
        data = self.db.fetch_one(query, params)
        if not data:
            return None
        return dict(data)