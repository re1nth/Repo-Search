import os
import ollama
import time
import sys
from langchain_ollama import ChatOllama  # Correct import path for the new package
from langchain.text_splitter import RecursiveCharacterTextSplitter
from prompts import (
    GENERAL_SUMMARY_PROMPT_TEMPLATE,
    FILE_SUMMARY_PROMPT_TEMPLATE,
    FOLDER_SUMMARY_PROMPT_TEMPLATE,
    ROOT_PROJECT_SUMMARY_PROMPT_TEMPLATE
)

# Initialize LangChain's Ollama wrapper for LLaMA 3.2
llm = ChatOllama(model="llama3.2")

def delete_sumy_files(directory):
    """
    Recursively traverses the given directory and deletes all .sumy files.
    
    Args:
        directory (str): The path to the repository.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.sumy'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")

def generate_summary(content, context="code"):
    """
    Uses the locally running Llama 3.2 model via Ollama to summarize the given content.
    """
    prompt = GENERAL_SUMMARY_PROMPT_TEMPLATE.format(context=context, content=content)
    response = llm.invoke(prompt)
    return response.content.strip()

def recursive_summarize_text(text, context="code", max_tokens=131072):
    """
    Recursively summarizes the text using LangChain's RecursiveCharacterTextSplitter.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=200
    )

    chunks = splitter.split_text(text)

    if len(chunks) == 1:
        return generate_summary(text, context)

    # Summarize each chunk and combine results
    partial_summaries = [generate_summary(chunk, context) for chunk in chunks]
    combined_summary = "\n".join(partial_summaries)

    # Recurse until the combined summary fits within the token limit
    return recursive_summarize_text(combined_summary, context, max_tokens)

def generate_file_summary(file_name, content):
    prompt = FILE_SUMMARY_PROMPT_TEMPLATE.format(file_name=file_name, content=content)
    return recursive_summarize_text(prompt, context="file structured")

def generate_folder_summary(folder_path, file_summaries, subfolder_summaries):
    combined_context = ""
    for fname, summary in file_summaries.items():
        combined_context += f"File Summary - {fname}:\n{summary}\n\n"
    for subfolder, summary in subfolder_summaries.items():
        combined_context += f"Subfolder Summary - {subfolder}:\n{summary}\n\n"

    prompt = FOLDER_SUMMARY_PROMPT_TEMPLATE.format(folder_path=folder_path, context=combined_context)
    return recursive_summarize_text(prompt, context="folder structured")

def generate_root_project_summary(folder_path, combined_context):
    prompt = ROOT_PROJECT_SUMMARY_PROMPT_TEMPLATE.format(folder_path=folder_path, context=combined_context)
    return recursive_summarize_text(prompt, context="project summary")

def traverse_and_summarize(folder_path, repo_path):
    subfolder_summaries = {}
    for entry in os.listdir(folder_path):
        full_path = os.path.join(folder_path, entry)
        if os.path.isdir(full_path) and not os.path.basename(full_path).startswith('.'):
            traverse_and_summarize(full_path, repo_path)
            subfolder_name = os.path.basename(full_path)
            summary_file = os.path.join(full_path, f"{subfolder_name}.sumy")
            if os.path.exists(summary_file):
                with open(summary_file, "r", encoding="utf-8") as f:
                    subfolder_summaries[entry] = f.read()
            else:
                subfolder_summaries[entry] = "No summary available."

    file_summaries = {}
    for entry in os.listdir(folder_path):
        full_path = os.path.join(folder_path, entry)
        if os.path.isfile(full_path) and not entry.endswith(".sumy"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                file_summaries[entry] = generate_file_summary(entry, content)
            except Exception as e:
                file_summaries[entry] = f"Error reading file: {e}"

    combined_context = ""
    for fname, summary in file_summaries.items():
        combined_context += f"File Summary - {fname}:\n{summary}\n\n"
    for subfolder, summary in subfolder_summaries.items():
        combined_context += f"Subfolder Summary - {subfolder}:\n{summary}\n\n"

    folder_name = os.path.basename(os.path.normpath(folder_path)) or "root"

    if os.path.abspath(folder_path) == os.path.abspath(repo_path):
        final_summary = generate_root_project_summary(folder_path, combined_context)
    else:
        final_summary = generate_folder_summary(folder_path, file_summaries, subfolder_summaries)

    summary_filename = os.path.join(folder_path, f"{folder_name}.sumy")
    with open(summary_filename, "w", encoding="utf-8") as f:
        f.write(final_summary)

    print(f"Summary written for {folder_path} to {summary_filename}")

def read_any_root_sumy(repo_path):
    for entry in os.listdir(repo_path):
        if entry.endswith(".sumy"):
            with open(os.path.join(repo_path, entry), "r", encoding="utf-8") as f:
                return f.read()
    print("No .sumy file found in the root directory.")
    return None

if __name__ == '__main__':

    # Redirect all output to a file
    with open("sequential-results.txt", "w") as f:
        sys.stdout = f  # Redirect stdout to results.txt
    
        repo_path = "/Users/reva/Documents/geek_projects/dungbeetle"
        delete_sumy_files(repo_path)
    
        start_time = time.time()
        traverse_and_summarize(repo_path, repo_path)
        end_time = time.time()
    
        print(f"Time taken to execute the summary calculation in serial: {end_time - start_time:.6f} seconds")
    
        summary_output = read_any_root_sumy(repo_path)
        if summary_output:
            print("\n--- Root Project Summary ---\n")
            print(summary_output)
            
    sys.stdout = sys.__stdout__  # Reset stdout back to normal