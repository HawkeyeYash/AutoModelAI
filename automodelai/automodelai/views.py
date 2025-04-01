import os
from dotenv import load_dotenv
load_dotenv()
from autogen.coding import LocalCommandLineCodeExecutor
from autogen import ConversableAgent, AssistantAgent
import pandas as pd
from autogluon.tabular import TabularDataset, TabularPredictor
import shutil
from sklearn.model_selection import train_test_split
from django.shortcuts import render
from django.conf import settings

llm_config0 = {
    "model": "llama3-70b-8192",
    "api_key": os.environ.get("GROQ_API_KEY"),
    "api_type": "groq",
    "temperature": 0.0,
    }

llm_config1 = {
    "model": "llama3-70b-8192",
    "api_key": os.environ.get("GROQ_API_KEY"),
    "api_type": "groq",
    "temperature": 0.1,
    }

executor = LocalCommandLineCodeExecutor(
timeout=60,
work_dir="coding",
)

code_executor_agent = ConversableAgent(
name="code_executor_agent",
llm_config=False,
code_execution_config={"executor": executor},
human_input_mode="NEVER",
default_auto_reply=
"Please continue. If everything is done, just only reply 'TERMINATE'.",
max_consecutive_auto_reply=7)



def user_home(request):
    return render(request,"user-home.html")

def projectinfo(request):
    return render(request,"projectinfo.html")

def about(request):
    return render(request,"aboutus.html")

def project(request):
    return render(request,"project.html")

def clean_data(request):
    if request.method == 'POST':
        data = request.FILES.get('dataset')

        if not data:
            return render(request, "project.html", {'model_insights_and_analysis': "No file uploaded."})

        try:
            code_writer_agent = AssistantAgent(
            name="code_writer_agent",
            llm_config=llm_config0,
            code_execution_config=False,
            human_input_mode="NEVER",
            )
            os.makedirs(settings.CODING_DIR, exist_ok=True)
            file_path = os.path.join(settings.CODING_DIR, data.name)
            
            with open(file_path, "wb") as f:
                f.write(data.read())

            message = f"""
            STRICTLY perform these steps on '{file_path}':
            1. Load data with pandas
            2. Show data.head() first
            3. Remove EXACT duplicate rows (keep first occurrence)
            4. Impute with median if Null or NaN value is present in Int or float column.
            5. For numeric columns:
               - Remove ALL non-numeric characters (units, symbols, spaces) using apply(lambda x: re.sub('[^0-9]', '', str(x)))
               and pd.to_numeric functionalities.
               - Convert to integers using astype(int), ensuring no non-numeric values remain.
            6. DO NOT modify non-numeric columns (IDs, names, etc.) that contain mixed object and integer values.
            7. Convert fonts to Arial formatting.
            8. ONLY save cleaned data as 'cleaned_data.csv'.
            9. DO NOT create any other files or visualizations.
            """

            chat_result = code_executor_agent.initiate_chat(
            code_writer_agent,
            message=message,
            )
            
            cleaned_file_path = os.path.join(settings.CODING_DIR, "cleaned_data.csv")
            df_cleaned = pd.read_csv(cleaned_file_path)

            cleaned_table_html = df_cleaned.to_html(classes="table table-bordered table-striped", index=False)

            output = "Data cleaning and preprocessing completed successfully."
        except Exception as e:
            output = f"Error processing file: {str(e)}"
            cleaned_table_html = None

    else:
        output = "Invalid request method."

    return render(request, "project.html", {'model_insights_and_analysis': output, 'cleaned_table_html': cleaned_table_html})

def analyze_data(request):
    if request.method == 'POST':
        try:
            image_files = []
            code_writer_agent = AssistantAgent(
            name="code_writer_agent",
            llm_config=llm_config1,
            code_execution_config=False,
            human_input_mode="NEVER",
            )
            message = f"""
            STRICTLY analyze 'cleaned_data.csv':
            1. Use ONLY pandas and seaborn
            2. For each numeric column:
            - Generate histogram (no outliers)
            - Generate boxplot (show outliers)
            3. Save plots as PNG in 'visualizations' folder:
            - Format: 'hist_[column].png', 'box_[column].png'
            - Use Arial font
            4. Save analysis in 'analysis_insights.txt'
            5. DO NOT show plots - ONLY save files
            """

            chat_result = code_executor_agent.initiate_chat(
            code_writer_agent,
            message=message,
            )
            analysis_save_path = os.path.join(settings.CODING_DIR, "analysis_insights.txt")
            with open(analysis_save_path, "r", encoding="utf-8", errors="replace") as n:
                output = n.read()

            src_folder = os.path.join(settings.CODING_DIR, "visualizations")
            dest_folder = os.path.join(settings.MEDIA_ROOT, "visualizations")
            if not os.path.exists(dest_folder):
                os.makedirs(dest_folder)

            if os.path.exists(src_folder):
                for file in os.listdir(src_folder):
                    if file.endswith('.png'):
                        src_path = os.path.join(src_folder, file)
                        dest_path = os.path.join(dest_folder, file)

                        if not os.path.exists(dest_path):
                            shutil.copy2(src_path, dest_path)
                        
                        image_files.append(f"{settings.MEDIA_URL}visualizations/{file}")

            cleaned_file_path = os.path.join(settings.CODING_DIR, "cleaned_data.csv")
            df_cleaned = pd.read_csv(cleaned_file_path)

            cleaned_table_html = df_cleaned.to_html(classes="table table-bordered table-striped", index=False)

        except Exception as e:
            output = f"Error processing file: {str(e)}"
            cleaned_table_html = None

    else:
        output = "Invalid request method."

    return render(request, "project.html", {'model_insights_and_analysis': output, 'image_files': image_files, 'cleaned_table_html': cleaned_table_html})

def model_data(request):
    if request.method == 'POST':
        try:
            image_files = []
            code_writer_agent = AssistantAgent(
            name="code_writer_agent",
            llm_config=llm_config1,
            code_execution_config=False,
            human_input_mode="NEVER",
            )
            # Load dataset and split
            df = pd.read_csv(os.path.join(settings.CODING_DIR, "cleaned_data.csv"))
            train_data, test_data = train_test_split(df, test_size=0.2, random_state=42)
            train_data = TabularDataset(train_data)
            label = str(df.columns[-1])

            # Train model
            predictor = TabularPredictor(label=label).fit(train_data)
            test_data = TabularDataset(test_data)

            # Evaluate model
            results = predictor.evaluate(test_data, silent=True)
            results_str = str(results)

            leaderboard = predictor.leaderboard(test_data)
            leaderboard_csv_path = os.path.join(settings.CODING_DIR, "model_leaderboard.csv")
            leaderboard.to_csv(leaderboard_csv_path, index=False)
            
            message = f"""
            Model Leaderboard: "model_leaderboard.csv" file which contains all model performance for 'cleaned_data.csv'.
            Main Evaluation Results: {results_str}

            Perform the following tasks:
            1. Write your assessment about them. Is the model good or bad? and Why?
            2. IMPORTANT - Save your assessment in model_insights.txt file in utf-encoding only."""
            
            chat_result = code_executor_agent.initiate_chat(
                code_writer_agent,
                message=message,
            )

            model_insights_path = os.path.join(settings.CODING_DIR, "model_insights.txt")

            with open(model_insights_path, "r", encoding="utf-8") as f:
                insights_content = f.read()

            with open(model_insights_path, "a", encoding="utf-8") as f:
                f.write("\n\n### Model Evaluation Results ###\n")
                f.write(str(results))
                f.write("\n\n### Model Leaderboard ###\n")
                f.write(leaderboard.to_string())

            with open(model_insights_path, "r", encoding="utf-8") as f:
                output = f.read()
            
            src_folder = os.path.join(settings.MEDIA_ROOT, "visualizations")
            if os.path.exists(src_folder):
                image_files = [
                    f"{settings.MEDIA_URL}visualizations/{file}"
                    for file in os.listdir(src_folder) if file.endswith('.png')
                ]
            cleaned_file_path = os.path.join(settings.CODING_DIR, "cleaned_data.csv")
            df_cleaned = pd.read_csv(cleaned_file_path)

            cleaned_table_html = df_cleaned.to_html(classes="table table-bordered table-striped", index=False)

        except Exception as e:
            output = f"Error processing file: {str(e)}"
            cleaned_table_html = None
    
    else:
        output = "Invalid request method."

    return render(request, "project.html", {'model_insights_and_analysis': output, 'image_files': image_files, 'cleaned_table_html': cleaned_table_html})
