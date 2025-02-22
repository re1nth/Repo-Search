# prompts.py

GENERAL_SUMMARY_PROMPT_TEMPLATE = (
    "Please provide a plain English summary of the following {context} content "
    "that explains its high-level functionality:\n\n"
    "{content}\n\nSummary:"
)

FILE_SUMMARY_PROMPT_TEMPLATE = (
    "Please provide a structured summary for the file '{file_name}' that includes:\n"
    "- Dependencies: All major dependencies (e.g., database, storage, major software components).\n"
    "- Modules: The major software modules used (e.g., authentication, business logic).\n"
    "- Workflows: High-level and important workflows implemented in the project.\n"
    "- Functionality: A high-level description of the functionality achieved.\n\n"
    "File Content:\n{content}\n\n"
    "Provide the summary in the following format:\n"
    "File: {file_name}\n"
    "{{\nDependencies: ...\nModules: ...\nWorkflows: ...\nFunctionality: ...\n}}"
)

FOLDER_SUMMARY_PROMPT_TEMPLATE = (
    "Please provide a structured summary for the folder '{folder_path}' by combining the following summaries. "
    "For each file, ensure the summary includes Dependencies, Modules, Workflows, and Functionality. "
    "Then, produce a concise summary for the folder.\n\n"
    "Context:\n{context}\n\nFolder Summary:"
)

ROOT_PROJECT_SUMMARY_PROMPT_TEMPLATE = (
    "Based on the following folder summary context for the project at '{folder_path}', provide a structured project summary in the following format:\n\n"
    "Project One-liner: <One-line summary of the project>\n"
    "Dependencies: <List major dependencies like databases, storage, and key software components>\n"
    "Modules: <List the major software modules such as authentication, business logic, etc.>\n"
    "Workflows: <Describe high-level and important workflows implemented in the project>\n\n"
    "Context:\n{context}\n\nProject Summary:"
)
