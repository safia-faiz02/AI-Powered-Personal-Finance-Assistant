import base64
import os
from textwrap import dedent

import fitz  # PyMuPDF for PDF extraction
import streamlit as st
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from streamlit.delta_generator import DeltaGenerator

# Load AIML API Key from environment variables
aiml_key = os.getenv("AIML_API_KEY")
if not aiml_key:
    st.error("Please configure the AIML API key in environment variables.")
    st.stop()

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    return "".join(page.get_text() for page in doc)

# Function to query DeepSeek-R1 for spending analysis
def analyze_spending(file, income=5000):
    print("Analyzing spending patterns...")
    document_text = extract_text_from_pdf(file).strip()
    if not document_text.strip():
        st.error("No readable transactions found in the PDF. Please upload a valid statement.")
        return "Error: No recommendations generated."

    deepseek_model = ModelFactory.create(
        model_platform=ModelPlatformType.AIML,
        # model_type="deepseek/deepseek-r1",
        model_type="deepseek/deepseek-chat",
        model_config_dict={
            "max_tokens": 2000,
            "temperature": 0.7
        }
    )
    agent = ChatAgent(
        system_message=dedent("""
        You are a personal finance assistant that analyzes credit card transactions to identify spending patterns and provide recommendations for reducing unnecessary expenses, maximizing rewards, and budgeting effectively. You rely on budgeting principles, like the 50/30/20 rule (50% needs, 30% wants, 20% savings), zero-based budgeting, and predictive analytics, to help users manage their finances better.
        Your responses should be:
        - Clear, concise, and user-friendly.
        - Non-judgmental and focused on financial well-being.
        - Actionable, with personalized insights based on the user's spending habits."""),
        model=deepseek_model
    )

    # income = 5000  # Placeholder for monthly income. TODO: Extract from user input.
    
    input_message = dedent(f"""
    Please analyze the following fiancial data and provide recommendations. 

    ### **Financial Data:**
    - **Monthly Income**: ${income}
    - **Transactions**:
        <transactions>
        {document_text}
        </transactions>

    Follow these steps in your analysis:
    **Analysis Steps:**
    `1. Categorize each transaction into needs or wants.
    2. Sum up spending in each category and calculate the percentage of income allocated to each.
    3. Calculate total expenses as the sum of needs and wants.
    4. Calculate savings as the difference between income and total expenses.
    5. Identify any unnecessary or excessive purchases that deviate from usual spending patterns.
    6. Apply zero-based budgeting to optimize fund allocation and ensure every dollar is assigned purposefully.
    7. Use predictive analytics to anticipate future expenses and potential financial risks.`

    Respond in the following format:
    **Response Format:**
    `## Financial Analysis & Recommendations
    #### **Spending Breakdown (50/30/20 Rule):**
    - **Needs**: $X (Y% of income) ✅/❌ (compared to 50%)
    - **Wants**: $X (Y% of income) ✅/❌ (compared to 30%)
    - **Total Expenses**: $X (Y% of income)
    - **Savings (Income - Total Expenses)**: $X (Y% of income) ✅/❌ (compared to 20%)

    #### **Identified Spending Issues:**  
    - [List flagged spending issues, if any (don't force) such as exceeding budget limits, frequent impulse purchases, high-cost recurring expenses, etc.]

    #### **Actionable Recommendations:**  
    - [List personalized recommendations to optimize spending, cut unnecessary costs, maximize savings, and improve financial stability.]`

    Ensure your response is **clear, concise, and user-friendly**, focusing on **actionable insights** for better financial management.
    """)

    response = agent.step(input_message)
    return response.msgs[0].content if response and response.msgs else "No recommendations generated."

# Streamlit Interface
st.set_page_config(page_title="AI Finance Assistant", page_icon="💰")
st.title("AI-Powered Personal Finance Assistant")
st.markdown("**_Upload your credit card statement (PDF) and get personalized budgeting recommendations using AI and budgeting principles like the 50/30/20 rule, zero-based budgeting, and predictive analytics._**")  
st.divider()

# Get list of sample PDFs
sample_folder = "./sample_pdfs/"
sample_pdfs = [f for f in os.listdir(sample_folder) if f.endswith(".pdf")]
sample_pdfs.insert(0, "None (Upload Your Own)")  # Default option

uploaded_file = st.file_uploader("Upload Credit Card Statement (PDF)", type=["pdf"])
selected_sample = st.selectbox("Or choose a sample file:", sample_pdfs)
income = st.number_input("Enter your monthly income ($)", min_value=0, value=5000)
analysis_button = st.button("Analyze Spending")

# Determine which file to use
file_to_analyze = None
file_name = None

if uploaded_file:
    print("Using uploaded file")
    file_to_analyze = uploaded_file
    file_name = "Uploaded File"
elif selected_sample != "None (Upload Your Own)":
    print("Using sample file")
    file_path = os.path.join(sample_folder, selected_sample)
    file_to_analyze = open(file_path, "rb")
    file_name = selected_sample


# if file_to_analyze:
#     st.markdown("#### Preview")
#     pdf_bytes = file_to_analyze.read()
#     base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
#     pdf_display = f"""
#     <style>
#         .pdf-container {{
#             border: 2px solid #ccc;  /* Light grey border */
#             border-radius: 10px; /* Rounded corners */
#             overflow: hidden; /* Ensures rounded corners apply */
#             width: 100%;
#             height: 210px;
#             padding: 5px;
#         }}
#         .pdf-container iframe {{
#             width: 100%;
#             height: 100%;
#             border: none; /* Removes default iframe border */
#         }}
#     </style>
#     <div class="pdf-container">
#         <iframe src="data:application/pdf;base64,{base64_pdf}"></iframe>
#     </div>
#     """
#     st.markdown(pdf_display, unsafe_allow_html=True)

if analysis_button and file_to_analyze:
    st.divider()
    with st.spinner("Analyzing spending patterns..."):
        file_to_analyze.seek(0)  # Reset file position to beginning
        recommendations = analyze_spending(file_to_analyze, income).strip()

    if not recommendations:
        st.error("No recommendations generated.")
    elif "error" in recommendations.lower():
        st.error(recommendations)
    else:
        st.success("Analysis completed")
        st.markdown(recommendations, unsafe_allow_html=True)

# Close file if it was a sample
if selected_sample != "None (Upload Your Own)" and file_to_analyze:
    file_to_analyze.close()