import streamlit as st
from langchain_groq import ChatGroq
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage
)
from verifylead import verify_lead,extract_json_from_string
import json

st.set_page_config("Automotive Sales and Processes", "🚗","wide")
st.title("Automotive Sales and Processes")

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
)



system_prompt = """Instruction:
Extract the following details from the text:

Name
Email
Phone Number
Civil ID Number (12 digits)
Return the information in a json format.

Context:
The text may include personal details mixed with other information. The required fields could appear in different formats.
input may be single value please note that

Negative Prompting:
Do not extract unrelated data like addresses or social media handles.
Exclude incomplete emails or invalid phone numbers with empty strings "".
Avoid generic placeholders.
Dont Include Values that are not present in the given user input


Example:
Input:
karthick,karthick@example.com ,+919876543210,123456789012.

Output:
{"Name": "karthick", "Email": "karthick@example.com", "Phone Number": "+919876543210", "Civil ID Number": "123456789012"}
"""

if "messages" not in st.session_state:
    st.session_state["messages"] = [SystemMessage(content=system_prompt)]

if "output" not in st.session_state:
    st.session_state["output"] = []

def get_message_role(message):
    if isinstance(message, HumanMessage):
        return "User"
    elif isinstance(message, AIMessage):
        return "Assistant"
    return "unknown"

with st.chat_message("User"):
    st.markdown("Hi")
with st.chat_message("Assistant"):
    st.markdown("Hi, How May I Help You?")

for message in st.session_state.messages:
    if not isinstance(message,SystemMessage):
        role = get_message_role(message)
        with st.chat_message(role):
            st.markdown(message.content)

verify_lead_output = None

if prompt:= st.chat_input("Ask questions about the automotive sales and processes"):
    st.session_state.messages.append(HumanMessage(content=prompt))

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("Assistant"):
        response = llm.invoke(st.session_state.messages)
        st.write(response.content)
        json_resp_str = extract_json_from_string(response.content)
            
        
        if json_resp_str is None:
            json_resp_str = response.content

        st.session_state.messages.append(AIMessage(content=json_resp_str))
        
        try:
            json_resp = json.loads(json_resp_str)
            verify_lead_output  = verify_lead(
                            name=json_resp.get('Name',None),
                            email=json_resp.get('Email',None),
                            phone=json_resp.get('Phone Number',None),
                            civil_id=json_resp.get('Civil ID Number',None)
                        )
        except Exception as e:
            verify_lead_output = json_resp_str

        st.markdown(json_resp_str)
        print(verify_lead_output)

with st.sidebar:
    st.title("Output Tool Message To The Primary Agent")
    with st.container(border=True):
        if verify_lead_output:
            st.markdown(verify_lead_output)
        else:
            st.markdown("Please Give input To Proceed")