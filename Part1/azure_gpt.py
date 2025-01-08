from openai import AzureOpenAI
import json
from few_shot_examples import *

client = AzureOpenAI(
    api_version="2023-07-01-preview",
    azure_endpoint="https://<your-endpoint>.openai.azure.com/",
    api_key="<your-azure-openai-api-key>"
)

def parse_fields_to_json(ocr_data):
    """
    Use GPT to create a JSON file from extracted data
    """
    prompt = f"""You are a data organization expert specializing in processing forms and extracting structured information about individuals. Your task is to take raw text data from an OCR system, analyze it, and organize the extracted information into a well-structured JSON format.

    Instructions:
    Input Characteristics:
    
    - The input is a raw text string containing information extracted from a form.
    - The text may be in English or Hebrew.
    - It contains fields related to personal information, addresses, and medical details.
    
    Input OCR text may include errors such as:
    - Dates with incorrect separators (e.g., '02 05 1999' or '02|05|1999' or '0 2 02 1 99 5' and so on.).
    - Numbers split by '|' or 'l'.
    Output Requirements:
    
    If the input text is in English, produce a JSON file in the following structure:
    {{
      "lastName": "",
      "firstName": "",
      "idNumber": "",
      "gender": "",
      "dateOfBirth": {{
        "day": "",
        "month": "",
        "year": ""
      }},
      "address": {{
        "street": "",
        "houseNumber": "",
        "entrance": "",
        "apartment": "",
        "city": "",
        "postalCode": "",
        "poBox": ""
      }},
      "landlinePhone": "",
      "mobilePhone": "",
      "jobType": "",
      "dateOfInjury": {{
        "day": "",
        "month": "",
        "year": ""
      }},
      "timeOfInjury": "",
      "accidentLocation": "",
      "accidentAddress": "",
      "accidentDescription": "",
      "injuredBodyPart": "",
      "signature": "",
      "formFillingDate": {{
        "day": "",
        "month": "",
        "year": ""
      }},
      "formReceiptDateAtClinic": {{
        "day": "",
        "month": "",
        "year": ""
      }},
      "medicalInstitutionFields": {{
        "healthFundMember": "",
        "natureOfAccident": "",
        "medicalDiagnoses": ""
      }}
    }}
    
    If the input text is in Hebrew, produce a JSON file in the following structure:
   {{
      "שם משפחה": "",
      "שם פרטי": "",
      "מספר זהות": "",
      "מין": "",
      "תאריך לידה": {{
        "יום": "",
        "חודש": "",
        "שנה": ""
      }},
      "כתובת": {{
        "רחוב": "",
        "מספר בית": "",
        "כניסה": "",
        "דירה": "",
        "ישוב": "",
        "מיקוד": "",
        "תא דואר": ""
      }},
      "טלפון קווי": "",
      "טלפון נייד": "",
      "סוג העבודה": "",
      "תאריך הפגיעה": {{
        "יום": "",
        "חודש": "",
        "שנה": ""
      }},
      "שעת הפגיעה": "",
      "מקום התאונה": "",
      "כתובת מקום התאונה": "",
      "תיאור התאונה": "",
      "האיבר שנפגע": "",
      "חתימה": "",
      "תאריך מילוי הטופס": {{
        "יום": "",
        "חודש": "",
        "שנה": ""
      }},
      "תאריך קבלת הטופס בקופה": {{
        "יום": "",
        "חודש": "",
        "שנה": ""
      }},
      "למילוי ע\"י המוסד הרפואי": {{
        "חבר בקופת חולים": "",
        "מהות התאונה": "",
        "אבחנות רפואיות": ""
      }}
   }}
    
    Special considerations:
    - Every phone number (home or mobile) must start with a 0, if you recognize another digit in the first place, make it 0.
    - If a field is missing or cannot be extracted, leave it as an empty string in the JSON.
    - Pay attention to the text language and ensure the appropriate format is used.
    - Handle date fields by extracting the day, month, and year separately.
    - All of the Date formats in this file are : "dd/mm/yyyy". so "0" cannot be a day.
    - The date may appear as : "ddmm yyy y" or "d dmm yy y y" or "d  d m m y y y y" or any other format that include dd-mm-yyyy with spaces between them. just consider the order.
    - The part of "healthFundMember" both in english and in hebrew, must only be extracted from section 5 of the file.
    - A landline(טלפון קווי) phone will never start with "05..", if you see "05" as the first 2 digits, it is a mobile number (טלפון נייד).
    
    
    Output MUST follow those guidelines:
    - Normalize dates into the format 'DD-MM-YYYY'.
    - Combine numbers split by '|' or 'l'.
    - MUST follow the JSON structure above.
    - The JSON must be clear, concise, and correctly formatted.
    - Ensure proper handling of Hebrew and English text.
    
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Extract the text from the data, following the above guidelines: {ocr_output_example}"},
            {"role": "assistant", "content": json.dumps(gt_example)},
            {"role": "user", "content": f"Extract the text from the data, following the above guidelines: {ocr_data['text']}"}
        ],
        max_tokens=1000
    )

    # GPT reply
    raw_content = response.choices[0].message.content.strip()

    json_block = None
    if "```json" in raw_content:
        try:
            # Extract content within "```json" block
            json_block = raw_content.split("```json")[1].split("```")[0].strip()
        except IndexError:
            raise ValueError(f"Malformed JSON block in response: {raw_content}")
    else:
        # The content is JSON formatted
        json_block = raw_content

    # Validate and parse JSON
    if not json_block.strip():
        raise ValueError("Empty JSON response from GPT model.")

    try:
        parsed_json = json.loads(json_block)
        return parsed_json
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {json_block}") from e



