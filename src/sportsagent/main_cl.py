# import uuid

# import chainlit as cl

# from sportsagent import utils
# from sportsagent.config import settings, setup_logging
# from sportsagent.models.chatbotstate import ChatbotState
# from sportsagent.workflow import graph

# logger = setup_logging(__name__)


# @cl.on_message
# async def main(message: cl.Message):
#     # Get user query
#     user_query = message.content
#     logger.info(f"Processing user query: '{user_query[:50]}...'")

#     # Get workflow and conversation history from session
#     workflow = cl.user_session.get("workflow")
#     conversation_history = cl.user_session.get("conversation_history", [])
#     if not isinstance(conversation_history, list):
#         conversation_history = []
#     session_id = cl.user_session.get("session_id")
#     if not session_id:
#         raise ValueError("Session ID not found in user session")

#     if workflow is None:
#         logger.error("Workflow not initialized in session")
#         await cl.Message(
#             content="Failed to initialize the chatbot workflow. Please try again later."
#         ).send()
#         return

#     # Create a message for processing indicator
#     processing_msg = cl.Message(content="Starting...")
#     await processing_msg.send()

#     try:
#         # Show processing indicator
#         processing_msg.content = "⏳ Processing your query..."
#         await processing_msg.update()

#         # Initialize state for workflow
#         initial_state: ChatbotState = ChatbotState(
#             messages=[],
#             user_query=user_query,
#             parsed_query=None,
#             generated_response="",
#             conversation_history=conversation_history,
#             session_id=session_id,
#         )
#         logger.info("Invoking LangGraph workflow")

#         # Update processing indicator
#         if conversation_history:
#             processing_msg.content = "🔍 Analyzing your question (using conversation context)..."
#         else:
#             processing_msg.content = "🔍 Analyzing your question..."
#         await processing_msg.update()

#         # Execute workflow
#         config = {"configurable": {"thread_id": session_id}}
#         final_state = workflow.invoke(initial_state, config=config)

#         # Check for interrupts (visualization or approval)
#         snapshot = workflow.get_state(config)

#         while snapshot.next:
#             if "visualization" in snapshot.next:
#                 # We are paused before visualization
#                 # Remove processing indicator temporarily
#                 await processing_msg.remove()

#                 # Ask user for approval
#                 res = await cl.AskUserMessage(
#                     content="Do you want to generate a visualization? (yes/no)", timeout=60
#                 ).send()

#                 # Re-show processing indicator
#                 processing_msg = cl.Message(content="Resuming...")
#                 await processing_msg.send()

#                 if res and res.get("output", "").lower() in ["yes", "y"]:
#                     # Resume
#                     processing_msg.content = "📊 Generating visualization..."
#                     await processing_msg.update()
#                     # Resume execution
#                     final_state = workflow.invoke(None, config=config)
#                 else:
#                     # Skip visualization
#                     logger.info("User skipped visualization")
#                     # We use the current state (from analyzer)
#                     break

#             elif "approval" in snapshot.next:
#                 # We are paused before retrieving more data
#                 current_state = snapshot.values
#                 new_query = current_state.get("user_query", "unknown query")

#                 await processing_msg.remove()

#                 res = await cl.AskUserMessage(
#                     content=f"The agent wants to request more data for: '{new_query}'. Approve? (yes/no)",
#                     timeout=60,
#                 ).send()

#                 processing_msg = cl.Message(content="Resuming...")
#                 await processing_msg.send()

#                 if res and res.get("output", "").lower() in ["yes", "y"]:
#                     processing_msg.content = f"🔄 Retrieving data for: {new_query}..."
#                     await processing_msg.update()
#                     final_state = workflow.invoke(None, config=config)
#                 else:
#                     logger.info("User rejected data retrieval")
#                     # If rejected, we should probably exit or return to analyzer?
#                     # For now, let's just break and show what we have
#                     break
#             else:
#                 # Unknown interrupt
#                 break

#             # Update snapshot after resume
#             snapshot = workflow.get_state(config)

#         logger.info("Workflow execution completed")

#         # Remove processing indicator
#         await processing_msg.remove()

#         # Get the generated response
#         response = final_state.get("generated_response", "")
#         error = final_state.get("error")

#         # Handle errors
#         if error:
#             logger.warning(f"Workflow completed with error: {error}")
#             if not response:
#                 response = "I'm sorry, I couldn't process your request due to an error. "

#         # Check if we have a response
#         if not response:
#             logger.error("No response generated by workflow")
#             response = "I'm sorry, I couldn't generate a response to your query. Please try rephrasing your question. "

#         # Check for visualization
#         elements = []
#         visualization = final_state.get("visualization")
#         if visualization:
#             elements.append(cl.Plotly(name="chart", figure=visualization, display="inline"))

#         # TODO: Stream the response back to the user
#         response_msg = cl.Message(content="", elements=elements)
#         await response_msg.send()

#         response_msg.content = response
#         await response_msg.update()

#         logger.info(f"Response sent to user ({len(response)} chars)")

#         # Update conversation history in session
#         updated_history = final_state.get("conversation_history", conversation_history)
#         cl.user_session.set("conversation_history", updated_history)

#         logger.info(f"Conversation history updated ({len(updated_history)} turns)")

#     except Exception as e:
#         logger.error(f"Error during message processing: {e}")
#         error_info = utils.map_exception_to_error(e)

#         # Remove processing indicator
#         try:
#             await processing_msg.remove()
#         except Exception:
#             pass

#         # Send user-friendly error message
#         await cl.Message(content=error_info["user_message"]).send()


# @cl.on_chat_start
# async def start():
#     session_id = str(uuid.uuid4())
#     cl.user_session.set("session_id", session_id)
#     logger.info(f"Started session: {session_id}")

#     # Send welcome message
#     await cl.Message(
#         content=utils.get_prompt_template("welcome-message.j2").render(session_id=session_id)
#     ).send()

#     try:
#         cl.user_session.set("workflow", graph)

#         # Initialize empty conversation history
#         cl.user_session.set("conversation_history", [])

#     except Exception as e:
#         logger.error(f"Error during chat start for session: {session_id}: {e}")
#         await cl.Message(content="Error initializing the chatbot.").send()


# @cl.on_chat_end
# async def end():
#     session_id = cl.user_session.get("session_id")
#     logger.info(f"Chat session ended: {session_id}")


# @cl.on_settings_update
# async def settings_update(settings: dict):
#     logger.info(f"Settings updated: {settings}")


# if __name__ == "__main__":
#     if not settings.OPENAI_API_KEY:
#         raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
#     cl.run()
