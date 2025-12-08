# Copilot Instructions

## General Instructions
- This project is a Python application managed with `uv`.

## General Guidelines
- Always ask for clarification if the request is not clear or there are multiple routes to consider.


## Generation Guidelines
- Never present generated, inferred, speculated or deduced content as fact.
- Label unverified content at the start of a sentence using [Inference] [Speculation] [Unverified].

## Style and Conventions
-  Always include type hints for function parameters and return types.
-  Use descriptive variable and function names.
-  Do not add comments or explanations in the code unless specifically requested.
-  All Python source files should have a logger instance.
-  Do not add function docstrings which do not provide additional information beyond the function name and it's parameters.
-  New functions should always start with a try catch with a logger.error in the catch block and the exception to be re-raised.
-  Use f-strings for string formatting.


## Project Notes
- deepagent implementation is deprecated and current focus is langgraph implementation starting from main_st.py