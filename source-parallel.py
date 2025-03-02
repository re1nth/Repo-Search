import ollama
import os
import asyncio
import concurrent.futures
import ollama
import time
import sys

from prompts import (
    GENERAL_SUMMARY_PROMPT_TEMPLATE,
    FILE_SUMMARY_PROMPT_TEMPLATE,
    FOLDER_SUMMARY_PROMPT_TEMPLATE,
    ROOT_PROJECT_SUMMARY_PROMPT_TEMPLATE
)

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

async def async_generate_summary(content, context="code", executor=None):
    """
    Asynchronous wrapper for generate_summary, offloaded to the executor.
    """
    loop = asyncio.get_running_loop()
    prompt = GENERAL_SUMMARY_PROMPT_TEMPLATE.format(context=context, content=content)
    # Offload the blocking call to the executor.
    return await loop.run_in_executor(
        executor,
        lambda: _blocking_generate_summary(prompt)
    )

def _blocking_generate_summary(prompt):
    """
    Blocking version of summary generation using ollama.
    """
    result = ""
    for chunk in ollama.chat(
        model="llama3.2",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    ):
        result += chunk["message"]["content"]
    return result.strip()

async def async_recursive_summarize_text(text, context="code", max_length=131072, executor=None):
    """
    Recursively summarizes text asynchronously. If the text exceeds max_length,
    splits it into chunks, summarizes each chunk concurrently, then summarizes
    the combined summaries.
    """
    if len(text) <= max_length:
        return await async_generate_summary(text, context, executor)
    else:
        chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
        partial_tasks = [
            async_recursive_summarize_text(chunk, context, max_length, executor)
            for chunk in chunks
        ]
        partial_summaries = await asyncio.gather(*partial_tasks)
        combined = "\n".join(partial_summaries)
        return await async_recursive_summarize_text(combined, context, max_length, executor)

async def async_generate_file_summary(file_name, content, executor=None):
    """
    Generates a structured summary for an individual file asynchronously.
    """
    prompt = FILE_SUMMARY_PROMPT_TEMPLATE.format(file_name=file_name, content=content)
    return await async_recursive_summarize_text(prompt, context="file structured", executor=executor)

async def async_generate_folder_summary(folder_path, file_summaries, subfolder_summaries, executor=None):
    """
    Generates a summary for a non-root folder asynchronously by combining file and subfolder summaries.
    """
    combined_context = ""
    for fname, summary in file_summaries.items():
        combined_context += f"File Summary - {fname}:\n{summary}\n\n"
    for subfolder, summary in subfolder_summaries.items():
        combined_context += f"Subfolder Summary - {subfolder}:\n{summary}\n\n"
    prompt = FOLDER_SUMMARY_PROMPT_TEMPLATE.format(folder_path=folder_path, context=combined_context)
    return await async_recursive_summarize_text(prompt, context="folder structured", executor=executor)

async def async_generate_root_project_summary(folder_path, combined_context, executor=None):
    """
    Generates the project-level summary for the root folder asynchronously.
    """
    prompt = ROOT_PROJECT_SUMMARY_PROMPT_TEMPLATE.format(folder_path=folder_path, context=combined_context)
    return await async_recursive_summarize_text(prompt, context="project summary", executor=executor)

# ---------------------------
# Asynchronous Traversal
# ---------------------------

async def async_traverse_and_summarize(folder_path, repo_path, executor=None):
    """
    Recursively traverses the repository asynchronously.
    Processes subdirectories (skipping hidden folders) and files concurrently.
    Writes a .sumy file for the folder and returns its summary.
    """
    subfolder_summaries = {}

    # Process subdirectories concurrently (skip hidden directories)
    subfolder_tasks = []
    subfolder_names = []
    for entry in os.listdir(folder_path):
        full_path = os.path.join(folder_path, entry)
        if os.path.isdir(full_path) and not os.path.basename(full_path).startswith('.'):
            subfolder_names.append(entry)
            subfolder_tasks.append(asyncio.create_task(async_traverse_and_summarize(full_path, repo_path, executor)))
    if subfolder_tasks:
        subfolder_results = await asyncio.gather(*subfolder_tasks, return_exceptions=True)
        for name, res in zip(subfolder_names, subfolder_results):
            subfolder_summaries[name] = res if not isinstance(res, Exception) else f"Error: {res}"

    # Process files concurrently (ignore .sumy files)
    file_summaries = {}
    file_tasks = {}
    for entry in os.listdir(folder_path):
        full_path = os.path.join(folder_path, entry)
        if os.path.isfile(full_path) and not entry.endswith(".sumy"):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                file_tasks[entry] = asyncio.create_task(async_generate_file_summary(entry, content, executor))
            except Exception as e:
                file_summaries[entry] = f"Error reading file: {e}"
    if file_tasks:
        file_results = await asyncio.gather(*file_tasks.values(), return_exceptions=True)
        for name, res in zip(file_tasks.keys(), file_results):
            file_summaries[name] = res if not isinstance(res, Exception) else f"Error: {res}"

    # Combine all file and subfolder summaries into one context
    combined_context = ""
    for fname, summary in file_summaries.items():
        combined_context += f"File Summary - {fname}:\n{summary}\n\n"
    for subfolder, summary in subfolder_summaries.items():
        combined_context += f"Subfolder Summary - {subfolder}:\n{summary}\n\n"

    folder_name = os.path.basename(os.path.normpath(folder_path)) or "root"
    if os.path.abspath(folder_path) == os.path.abspath(repo_path):
        final_summary = await async_generate_root_project_summary(folder_path, combined_context, executor)
    else:
        final_summary = await async_generate_folder_summary(folder_path, file_summaries, subfolder_summaries, executor)

    summary_filename = os.path.join(folder_path, f"{folder_name}.sumy")
    with open(summary_filename, "w", encoding="utf-8") as f:
        f.write(final_summary)
    print(f"Summary written for {folder_path} to {summary_filename}")
    return final_summary

def read_any_root_sumy(repo_path):
    """
    Reads and returns the content of any .sumy file found in the root directory.
    """
    for entry in os.listdir(repo_path):
        if entry.endswith(".sumy"):
            with open(os.path.join(repo_path, entry), "r", encoding="utf-8") as f:
                return f.read()
    print("No .sumy file found in the root directory.")
    return None

# ---------------------------
# Main Execution
# ---------------------------

if __name__ == '__main__':

    # Redirect all output to a file
    with open("parallel-results.txt", "w") as f:
        sys.stdout = f  # Redirect stdout to results.txt

        repo_path = "/Users/reva/Documents/geek_projects/dungbeetle"
        delete_sumy_files(repo_path)

        start_time = time.time()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=16)

        # Run the asynchronous traversal
        asyncio.run(async_traverse_and_summarize(repo_path, repo_path, executor))

        end_time = time.time()
        print(f"Time taken to execute the summary calculation in parallel : {end_time - start_time:.6f} seconds")

        summary_output = read_any_root_sumy(repo_path)
        if summary_output:
            print("\n--- Root Project Summary ---\n")
            print(summary_output)

    sys.stdout = sys.__stdout__  # Reset stdout back to normal
