import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()

INCOMING_DIR = "incoming_pdfs"

# Ensure the directory exists (create if not)
if not os.path.exists(INCOMING_DIR):
    os.makedirs(INCOMING_DIR)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Add a print statement to check if the API key is loaded
if GEMINI_API_KEY:
    print("GEMINI_API_KEY loaded successfully.")
else:
    print("GEMINI_API_KEY not found. Please ensure it\"s set in your environment variables.")

genai.configure(api_key=GEMINI_API_KEY)

# Updated model name based on available models from Render logs
model = genai.GenerativeModel("gemini-2.5-flash")

def load_rubric(rubric_name):
    try:
        with open("rubrics.json", "r") as f:
            rubrics = json.load(f)
        return rubrics.get(rubric_name)
    except FileNotFoundError:
        print("Error: rubrics.json not found.")
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode rubrics.json. Check JSON format.")
        return None

def format_rubric_for_prompt(rubric_data):
    if not rubric_data:
        return "No rubric provided."
    
    formatted_rubric = f"Rubric Name: {rubric_data.get("name", "N/A")}\n"
    formatted_rubric += f"Description: {rubric_data.get("description", "N/A")}\n\n"
    
    for criterion in rubric_data.get("criteria", []):
        formatted_rubric += f"Criteria: {criterion.get("title", "N/A")} ({criterion.get("points", 0)} points)\n"
        formatted_rubric += f"Description: {criterion.get("description", "N/A")}\n"
        formatted_rubric += "\n"
    return formatted_rubric

def grade_assignment(assignment_text, rubric_name="generic"):
    rubric_data = load_rubric(rubric_name)
    formatted_rubric = format_rubric_for_prompt(rubric_data)

    if not rubric_data:
        return {"error": f"Rubric {rubric_name} not found or could not be loaded."}

    # Define the JSON structure as a Python dictionary
    json_structure = {
        "student_name": "[Student's Name, extracted from the assignment if possible, otherwise 'Unknown']",
        "overall_grade": "[Overall percentage grade, e.g., '85%']",
        "feedback": "[Overall comprehensive feedback]",
        "criteria_scores": [
            {
                "criterion": "[Criterion Name]",
                "score": "[Score for this criterion]",
                "justification": "[Brief justification based on the rubric and submission]",
                "detalle": "[Where points were lost, if applicable]"
            }
        ]
    }

    # Convert the dictionary to a JSON string, handling all escaping automatically
    json_format_instruction = json.dumps(json_structure, indent=4)

    prompt = f"""You are an AI assistant acting as a Professional Lecturer or a Senior Teacher. Your task is to grade assignments based on the provided rubric. 
    
    Here is the rubric for the assignment:
    {formatted_rubric}

    Here is the student's assignment:
    {assignment_text}

    Please provide a detailed grading based on the rubric, including a score for each criterion and overall feedback. 
    Your response MUST be a valid JSON object ONLY. Do NOT include any other text, explanations, or formatting outside the JSON object. 
    The JSON object should strictly follow this format:
{json_format_instruction}
    """

    try:
        response = model.generate_content(prompt)
        print(f"Type of response from model.generate_content: {type(response)}")
        print(f"Content of response from model.generate_content: {response}")

        raw_response_text = ""
        if hasattr(response, 'text'):
            raw_response_text = response.text
        elif isinstance(response, str):
            raw_response_text = response
        else:
            raw_response_text = str(response)

        # Attempt to extract JSON from the raw response text
        json_start = raw_response_text.find('{')
        json_end = raw_response_text.rfind('}')

        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_string = raw_response_text[json_start : json_end + 1]
            try:
                json_response = json.loads(json_string)
                print(f"Successfully parsed JSON: {json_response}")
                return json_response
            except json.JSONDecodeError as e:
                print(f"Error decoding extracted JSON: {e}")
                print(f"Extracted JSON string: {json_string}")
                return {"error": f"Failed to parse AI response as JSON: {e}", "raw_response": raw_response_text}
        else:
            print(f"No valid JSON object found in AI response: {raw_response_text}")
            return {"error": "No valid JSON object found in AI response", "raw_response": raw_response_text}

    except Exception as e:
        print(f"Error during grading: {e}")
        return {"error": f"Error during grading: {e}"}

if __name__ == "__main__":
    # Example usage:
    sample_assignment = """The student solved the quadratic equation x^2 - 4x + 4 = 0 by factoring. They correctly identified that the equation factors to (x-2)^2 = 0, and thus x=2. The steps were clear and easy to follow. However, they did not show any work for how they arrived at the factored form.\n"""
    feedback = grade_assignment(sample_assignment, "generic")
    print(feedback)

    sample_assignment_history = """The essay discusses the causes of World War I. It mentions the assassination of Archduke Franz Ferdinand and the alliance system. However, it lacks in-depth analysis of other contributing factors like imperialism and militarism. The essay is well-structured but has some grammatical errors.\n"""
    feedback_history = grade_assignment(sample_assignment_history, "generic")
    print(feedback_history)