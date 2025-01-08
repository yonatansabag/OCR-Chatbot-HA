import streamlit as st
from azure_ocr import extract_text_from_document
from azure_gpt import parse_fields_to_json
from utils import validate_with_ground_truth, validate_dynamic_data
import json
import os


# Title Section
st.set_page_config(page_title="KPMG Assignment - Part 1", layout="wide")
st.title("📄 KPMG Home Assignment - Part 1")
st.markdown("Upload a PDF or image file to extract and validate data against ground truth.")

# File Upload Section
st.sidebar.header("Upload Section")
uploaded_file = st.sidebar.file_uploader(
    "Upload a PDF or Image File",
    type=["pdf", "jpg", "jpeg", "png"],
    help="Supported formats: PDF, JPG, PNG",
)
gt_directory = "gt"

if uploaded_file is not None:
    st.sidebar.success("File uploaded successfully!")
    with st.spinner("Processing your file... ⏳"):
        file = uploaded_file.read()

        # OCR
        ocr_output = extract_text_from_document(file)

        # Generate JSON Output
        st.subheader("🧠 Extracted JSON")
        json_output = parse_fields_to_json(ocr_output)
        st.json(json_output)

        json_output_str = json.dumps(json_output, indent=4, ensure_ascii=False)

        # Download Button
        st.download_button(
            label="💾 Download Extracted JSON",
            data=json_output_str,
            file_name=f"{uploaded_file.name.split('.')[0]}.json",
            mime="application/json",
        )

        # Validation Section
        st.subheader("✅ Validation Results")
        gt_filename = f"{uploaded_file.name.split('.')[0]}_gt.json"
        gt_path = os.path.join(gt_directory, gt_filename)

        if os.path.exists(gt_path):
            # Validation with GT
            with open(gt_path, "r", encoding="utf-8") as f:
                ground_truth = json.load(f)

            validation_results = validate_with_ground_truth(json_output, ground_truth)
            st.write("Validation Results (Against Ground Truth):")

            # Display mismatched fields if they exist
            if validation_results.get("mismatched_fields"):
                st.error("⚠️ Mismatched Fields Detected")
                st.json(validation_results["mismatched_fields"])

            if validation_results.get("missing_fields"):
                st.error("⚠️ Missing Fields Detected")
                st.write(", ".join(validation_results["missing_fields"]))
        else:
            # Dynamic Validation - Checks mostly completeness
            validation_results = validate_dynamic_data(json_output)
            st.write("Validation Results (Dynamic):")

            # Display missing fields for dynamic validation
            if validation_results.get("missing_fields"):
                st.warning("⚠️ Missing Fields Detected")
                st.write(", ".join(validation_results["missing_fields"]))

        # Display Validation Results
        # st.json(validation_results)

        # Summary Metrics
        accuracy = validation_results.get("accuracy", 0.0)
        completeness = validation_results.get("completeness", 0.0)

        col1, col2 = st.columns(2)
        col1.metric("🔍 Accuracy", f"{accuracy:.2f}%")
        col2.metric("📋 Completeness", f"{completeness:.2f}%")

else:
    st.sidebar.info("Awaiting file upload...")
    st.markdown("👈 Please upload a file from the sidebar to get started.")

