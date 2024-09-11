import phonenumbers
from email_validator import validate_email, EmailNotValidError
from phonenumbers import NumberParseException, is_valid_number
import re
from langchain_community.graphs import Neo4jGraph
from pyjarowinkler import distance

def graph_db():
    graph = Neo4jGraph()
    return graph
live_graph = graph_db()

def validate_email_address(email):
    """
    Validate the email address format and provide feedback to the lead agent.
    """
    try:
        valid = validate_email(email)
        email = valid.email
        return True
    except EmailNotValidError as e:
        return f"The email address '{email}' is invalid. Please verify and provide a correct email address format."

def validate_phone_number(number: str):
    """
    Validate the phone number format including the country code and provide feedback to the lead agent.
    """
    if not number.startswith('+'):
        return "The phone number must include the country code (e.g., +1 for the US). Please provide the correct format."

    if not number[1:].replace("-", "").replace(" ", "").isdigit():
        return "The phone number contains invalid characters. Ensure that it only contains digits, spaces, or hyphens after the country code."

    try:
        phone_number = phonenumbers.parse(number)
        if is_valid_number(phone_number):
            return True
        else:
            return f"The phone number '{number}' is not valid. Please double-check the number and try again."
    except NumberParseException:
        return f"An error occurred while validating the phone number '{number}'. Please verify that it is in the correct international format."

def validate_civil_id(civil_id):
    """
    Validate the Civil ID format and provide feedback to the lead agent.
    """
    civil_id_regex = r'^\d{12}$'

    if re.fullmatch(civil_id_regex, civil_id):
        return True
    else:
        return f"The Civil ID '{civil_id}' is invalid. A valid Civil ID should contain exactly 12 digits with no other characters."

def extract_json_from_string(s):
    # Regular expression to match the JSON part of the string
    json_pattern = re.compile(r'\{.*\}', re.DOTALL)
    
    # Search for the JSON pattern in the string
    match = json_pattern.search(s)
    
    if match:
        json_str = match.group(0)
        return json_str
    else:
        return None
    
def verify_lead(name: str = None, email: str = None, phone: str = None, civil_id: str = None):
    """
    Verify the existence of the Customer in our Database before lead creation.
    
    Parameters:
    - name: Customer's name (optional).
    - email: Customer's email (optional).
    - phone: Customer's phone (optional).
    - civil_id: Customer's civil ID (optional).
    
    Returns:
    - Clear and actionable messages for the lead agent to understand the verification results.
    """
    name, email, phone, civil_id = (None if x.strip() == "" else x for x in [name, email, phone, civil_id])


def verify_lead(name: str = None, email: str = None, phone: str = None, civil_id: str = None):
    """
    Verify the existence of the Customer in our Database before lead creation.
    
    Parameters:
    - name: Customer's name (optional).
    - email: Customer's email (optional).
    - phone: Customer's phone (optional).
    - civil_id: Customer's civil ID (optional).
    
    Returns:
    - Clear and actionable messages for the lead agent to understand the verification results.
    """
    def validation():
        phone_validation = True
        civil_validation = True
        email_validation = True

        if phone:
            phone_validation = validate_phone_number(phone)
            if phone_validation is not True:
                return phone_validation
        
        if civil_id:
            civil_validation = validate_civil_id(civil_id)
            if civil_validation is not True:
                return civil_validation
        
        if email:
            email_validation = validate_email_address(email)
            if email_validation is not True:
                return email_validation

        # If all validations pass, return True
        return all([phone_validation, civil_validation, email_validation])

    validated = validation()

    if validated == True:

        query = live_graph.query("""MATCH (c:Lead) RETURN c.name AS customer_name""")
        names_list = [name for i in query for name in [i['customer_name']]]

        def split_names(names):
            return [name.split(' ', 1) if ' ' in name else name for name in names]

        names_list = split_names(names_list)
        def similar_names(user_name, names_list, threshold=0.7):
            similar_names = []
            for name in names_list:
                if isinstance(name, str):
                    similarity = distance.get_jaro_distance(user_name, name)
                    if similarity >= threshold:
                        similar_names.append((name, similarity))
                else:
                    for i in name:
                        similarity = distance.get_jaro_distance(user_name, i)
                        if similarity >= threshold:
                            similar_names.append((' '.join(name), similarity))
            return similar_names

        if name and all(x is None for x in (phone, civil_id, email)):

            name_result = similar_names(name, names_list, threshold=0.8)
            print(name_result)
            if name_result:
                return f"The provided Name is associated with the following customer(s): {[i[0] for i in name_result]}. Would you like to proceed with one of these customers, or would you prefer to create a new lead?"        
            else:
                return f"No matching results were found for the name '{name}'. Please review or confirm the provided details. Would you like to create a new lead instead?"

        else:
            query = """
            MATCH (l:Lead)
            WHERE toLower(l.name) = toLower($name)
            """
            conditions = []
            if phone:
                conditions.append("l.phone_number = $phone")
            if civil_id:
                conditions.append("l.civil_id = $civil_id")
            if email:
                conditions.append("l.email = $email")
            
            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += """
            RETURN l.name AS lead_name, l.phone_number AS phone_number, l.civil_id AS civil_id, l.email AS email, l.id AS lead_id
            """        
            verified_result = live_graph.query(query, {
                'name': name,
                'phone': phone,
                'civil_id': civil_id,
                'email': email
            })

            if verified_result:
                return f"A customer named '{name}' already exists in our system with matching details (Phone: {verified_result[0]['phone_number']}, Email: {verified_result[0]['email']}, Civil ID: {verified_result[0]['civil_id']}). Would you like to proceed with this customer, or create a new lead?"
            
            else:        
                cypher_queries = []
                semi_verified_result = []

                if phone:
                    phone_query = """
                    MATCH (c:Lead)
                    WHERE c.phone_number = $phone 
                    RETURN c.name AS customer_name, c.phone_number AS phone_number, c.email AS email, c.civil_id AS civil_id
                    """
                    cypher_queries.append(("phone number", phone_query))

                if civil_id:
                    civil_id_query = """
                    MATCH (c:Lead) 
                    WHERE c.civil_id = $civil_id 
                    RETURN c.name AS customer_name, c.phone_number AS phone_number, c.email AS email, c.civil_id AS civil_id
                    """
                    cypher_queries.append(("civil ID", civil_id_query))

                if email:
                    email_query = """
                    MATCH (c:Lead) 
                    WHERE c.email = $email 
                    RETURN c.name AS customer_name, c.phone_number AS phone_number, c.email AS email, c.civil_id AS civil_id
                    """
                    cypher_queries.append(("email", email_query))

                for query_type, query in cypher_queries:
                    db_result = live_graph.query(query, {
                        'name': name,
                        'phone': phone,
                        'civil_id': civil_id,
                        'email': email
                    })

                    if db_result:
                        return f"I have identified that the {query_type} you provided is associated with {db_result[0]['customer_name']}. Could you please confirm or provide the correct {query_type} for {name}?"

                    else:
                        return f"I was unable to locate the {query_type} ({phone if query_type == 'phone number' else civil_id if query_type == 'civil ID' else email}) in our system. Would you like to proceed with creating a new lead?"
    else:return validated