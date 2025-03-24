from auto_eval_utils import encode_image
from PIL import Image
import re
import asyncio
MAX_IMAGE =50


def Autonomous_eval(task, last_actions, images_path) -> tuple[str, str]:
    system_msg = """You are an expert in evaluating the performance of a web navigation agent. The agent is designed to help a human user navigate a website to complete a task. Given the user's intent, the agent's action history, the final state of the webpage, and the agent's response to the user, your goal is to decide whether the agent's execution is successful or not.

There are three types of tasks:
1. Information seeking: The user wants to obtain certain information from the webpage, such as the information of a product, reviews, map info, comparison of map routes, etc. The bot's response must contain the information the user wants, or explicitly state that the information is not available. Otherwise, e.g. the bot encounters an exception and respond with the error content, the task is considered a failure. Besides, be careful about the sufficiency of the agent's actions. For example, when asked to list the top-searched items in a shop, the agent should order the items by the number of searches, and then return the top items. If the ordering action is missing, the task is likely to fail.
2. Site navigation: The user wants to navigate to a specific page. Carefully examine the bot's action history and the final state of the webpage to determine whether the bot successfully completes the task. No need to consider the bot's response.
3. Content modification: The user wants to modify the content of a webpage or configuration. Carefully examine the bot's action history and the final state of the webpage to determine whether the bot successfully completes the task. No need to consider the bot's response.

*IMPORTANT*
Format your response into two lines as shown below:

Thoughts: <your thoughts and reasoning process>
Status: "success" or "failure"
"""
    prompt = """User Intent: {task}

Action History:
{last_actions}

The last snapshot of the web page is shown in the image."""

    text = prompt.format(task=task, last_actions="\n".join(f"{i+1}. {action}" for i, action in enumerate(last_actions)))

    jpg_base64_str = encode_image(Image.open(images_path))
    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{jpg_base64_str}", "detail": "high"},
                },
            ],
        }
    ]
    return messages, text, system_msg

def AgentTrek_eval(task, last_actions, thoughts, images_path) -> tuple[str, str]:
    system_msg = """You are an expert in evaluating the performance of a web navigation agent. The agent is designed to help a human user navigate a website to complete a task. Given the user's task goal, the agent's trajectory, your goal is to decide whether the agent's execution is successful or not.

*Evaluation Criteria* 
Whether the agent's trajectory is effective and corresponding to the goal 

*Instructions* 1. Review the agent's actions and reasoning processes step by step. 
2. if the agent is stuck in the very first login stage, which means it fails to log into target website at the beginning, that's a failure. 
3. Determine if the agent has achieved the task goal based on the trajectory. A task can be considered successful if most trajectory is effective. 
4. the agent sometimes can't stop after finishing a task and continue doing repeated actions. these actions may be some failed attempt after a series of correct actions. the task should be regarded as successful if the correct actions are effective and almost reach the goal. 
5. if the agent is stuck in the loop at the early stage of the task, which means they don't even get close to the goal before they get stuck in the loop, that's a failure. for example, the agent begin to get stuck before third step. 
6. when the task is to change the google account password, it can't be regarded as successful when agent finish at trying to click "manage your account". 
7. if there are over 8 correct action in the trajectory, it can be regard as a successful agent. 
8. final saving action is not a must. the task is successful if the agent does most things right and just forget to save the change at last. 
9. if the original task has 2 subtasks, the agent only complete one of them, that's still a success. e.g. the task is to update name and birthday, but agent only update name, that's fine. 
10. if the task is to post a review, the agent can be considered successful when it finish writing the review and reach the step to post it, don't have to click the post button. 
11. Since we don't have a printer, some printing related task can be considered successful if the agent reach the step to click print button. 
12. if the task is finished at the initial state and the agent do nothing because of it, it should also be regarded as successful.

*IMPORTANT* 
1. in the trajectory, an action always follows a corresponding reasoning, which shows the observation and thought of the agent. 
2. your response should be contain: 
Thoughts: <your thoughts and reasoning process> 
Status: "success" or "failure"
"""
    prompt = """The goal of the task: {task}

Trajectory:
{thoughts_and_actions}

The last snapshot of the web page is shown in the image."""
    thoughts_and_actions = ""
    for idx, (thought, action) in enumerate(zip(thoughts, last_actions)):
        thought = thought.replace("\n\n", " ")
        action = action.replace("\n\n", " ")
        thoughts_and_actions += f"Thought {idx+1}: {thought}\nAction {idx+1}: {action}\n\n"
    text = prompt.format(task=task, thoughts_and_actions=thoughts_and_actions.strip("\n\n"))

    jpg_base64_str = encode_image(Image.open(images_path))
    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{jpg_base64_str}", "detail": "high"},
                },
            ],
        }
    ]
    return messages, text, system_msg


def WebVoyager_eval(task, images_path, response, k=0) -> tuple[str, str]:
    system_msg = """As an evaluator, you will be presented with three primary components to assist you in your role:

1. Web Task Instruction: This is a clear and specific directive provided in natural language, detailing the online activity to be carried out. These requirements may include conducting searches, verifying information, comparing prices, checking availability, or any other action relevant to the specified web service (such as Amazon, Apple, ArXiv, BBC News, Booking etc).

2. Result Screenshots: This is a visual representation of the screen showing the result or intermediate state of performing a web task. It serves as visual proof of the actions taken in response to the instruction.

3. Result Response: This is a textual response obtained after the execution of the web task. It serves as textual result in response to the instruction.

-- You DO NOT NEED to interact with web pages or perform actions such as booking flights or conducting searches on websites.
-- You SHOULD NOT make assumptions based on information not presented in the screenshot when comparing it to the instructions.
-- Your primary responsibility is to conduct a thorough assessment of the web task instruction against the outcome depicted in the screenshot and in the response, evaluating whether the actions taken align with the given instructions.
-- NOTE that the instruction may involve more than one task, for example, locating the garage and summarizing the review. Failing to complete either task, such as not providing a summary, should be considered unsuccessful.
-- NOTE that the screenshot is authentic, but the response provided by LLM is generated at the end of web browsing, and there may be discrepancies between the text and the screenshots.
-- Note the difference: 1) Result response may contradict the screenshot, then the content of the screenshot prevails, 2) The content in the Result response is not mentioned on the screenshot, choose to believe the content.

You should elaborate on how you arrived at your final evaluation and then provide a definitive verdict on whether the task has been successfully accomplished, either as 'SUCCESS' or 'FAILURE'."""
    prompt = """TASK: {task}

Result Response: {response}

{num} screenshots at the end: """

    whole_content_img = []
    images_path = images_path[:MAX_IMAGE]
    text = prompt.format(task=task, response=response, num = len(images_path) if k == 0 else k)

    for image in images_path[-k:]:
        jpg_base64_str = encode_image(Image.open(image))
        whole_content_img.append(
            {
                'type': 'image_url',
                'image_url': {"url": f"data:image/png;base64,{jpg_base64_str}", "detail": "high"}
            }
        )
    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [{"type": "text", "text": text}] 
            + whole_content_img
            + [{'type': 'text', 'text': "Your verdict:\n"}]
        }
    ]
    return messages, text, system_msg

async def identify_key_points(task, model):
    system_msg = """You are an expert tasked with analyzing a given task to identify the key points explicitly stated in the task description.

**Objective**: Carefully analyze the task description and extract the critical elements explicitly mentioned in the task for achieving its goal.

**Instructions**:
1. Read the task description carefully.
2. Identify and extract **key points** directly stated in the task description.
   - A **key point** is a critical element, condition, or step explicitly mentioned in the task description.
   - Do not infer or add any unstated elements.
   - Words such as "best," "highest," "cheapest," "latest," "most recent," "lowest," "closest," "highest-rated," "largest," and "newest" must go through the sort function(e.g., the key point should be "Filter by highest").

**Respond with**:
- **Key Points**: A numbered list of the explicit key points for completing this task, one per line, without explanations or additional details."""
    prompt = """Task: {task}"""
    text = prompt.format(task=task)
    messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text}
                ],
            }
        ]
    responses = await asyncio.to_thread(model.generate, messages)
    return responses[0]

async def judge_image(task, image_path, key_points, model):
    system_msg = """You are an expert evaluator tasked with determining whether an image contains information about the necessary steps to complete a task.

**Objective**: Analyze the provided image and decide if it shows essential steps or evidence required for completing the task. Use your reasoning to explain your decision before assigning a score.

**Instructions**:
1. Provide a detailed description of the image, including its contents, visible elements, text (if any), and any notable features.

2. Carefully examine the image and evaluate whether it contains necessary steps or evidence crucial to task completion:  
- Identify key points that could be relevant to task completion, such as actions, progress indicators, tool usage, applied filters, or step-by-step instructions.  
- Does the image show actions, progress indicators, or critical information directly related to completing the task?  
- Is this information indispensable for understanding or ensuring task success?
- If the image contains partial but relevant information, consider its usefulness rather than dismissing it outright.

3. Provide your response in the following format:  
- **Reasoning**: Explain your thought process and observations. Mention specific elements in the image that indicate necessary steps, evidence, or lack thereof.  
- **Score**: Assign a score based on the reasoning, using the following scale:  
    - **1**: The image does not contain any necessary steps or relevant information.  
    - **2**: The image contains minimal or ambiguous information, unlikely to be essential.  
    - **3**: The image includes some relevant steps or hints but lacks clarity or completeness.  
    - **4**: The image contains important steps or evidence that are highly relevant but not fully comprehensive.  
    - **5**: The image clearly displays necessary steps or evidence crucial for completing the task.

Respond with:  
1. **Reasoning**: [Your explanation]  
2. **Score**: [1-5]"""

    jpg_base64_str = encode_image(Image.open(image_path))

    prompt = """**Task**: {task}

**Key Points for Task Completion**: {key_points}

The snapshot of the web page is shown in the image."""
    text = prompt.format(task=task,key_points=key_points)

    messages = [
            {"role": "system", "content": system_msg},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{jpg_base64_str}", "detail": "high"},
                    },
                ],
            }
        ]

    responses = await asyncio.to_thread(model.generate, messages)
    return responses[0]

async def Online_Mind2Web_eval(task, last_actions, images_path, model, score_threshold):
    system_msg = """You are an expert in evaluating the performance of a web navigation agent. The agent is designed to help a human user navigate a website to complete a task. Given the user's task, the agent's action history, key points for task completion, some potentially important web pages in the agent's trajectory and their reasons, your goal is to determine whether the agent has completed the task and achieved all requirements.

Your response must strictly follow the following evaluation criteria!
*Important Evaluation Criteria*:
1: The filtered results must be displayed correctly. If filters were not properly applied (i.e., missing selection, missing confirmation, or no visible effect in results), the task is not considered successful.
2: You must carefully check whether these snapshots and action history meet these key points. Ensure that specific filter conditions, such as "best," "highest," "cheapest," "latest," "most recent," "lowest," "closest," "highest-rated," "largest," and "newest" are correctly applied using the filter function(e.g., sort function).
3: Certain key points or requirements should be applied by the filter. Otherwise, a search with all requirements as input will be deemed a failure since it cannot guarantee that all results meet the requirements!
4: If the task requires filtering by a specific range of money, years, or the number of beds and bathrooms, the applied filter must exactly match the given requirement. Any deviation results in failure. To ensure the task is successful, the applied filter must precisely match the specified range without being too broad or too narrow.
Examples of Failure Cases:
- If the requirement is less than $50, but the applied filter is less than $25, it is a failure.
- If the requirement is $1500-$2500, but the applied filter is $2000-$2500, it is a failure.
- If the requirement is $25-$200, but the applied filter is $0-$200, it is a failure.
- If the required years are 2004-2012, but the filter applied is 2001-2012, it is a failure.
- If the required years are before 2015, but the applied filter is 2000-2014, it is a failure.
- If the task requires exactly 2 beds, but the filter applied is 2+ beds, it is a failure.
5: Some tasks require a submission action or a display of results to be considered successful.
6: If the retrieved information is invalid or empty(e.g., No match was found), but the agent has correctly performed the required action, it should still be considered successful.
7: If the current page already displays all available items, then applying a filter is not necessary. As long as the agent selects items that meet the requirements (e.g., the cheapest or lowest price), the task is still considered successful.

*IMPORTANT*
Format your response into two lines as shown below:

Thoughts: <your thoughts and reasoning process based on double-checking each key points and the evaluation criteria>
Status: "success" or "failure"
"""
    prompt = """User Task: {task}

Key Points: {key_points}

Action History:
{last_actions}

The potentially important snapshots of the webpage in the agent's trajectory and their reasons:
{thoughts}"""


    key_points = await identify_key_points(task, model)
    key_points = key_points.replace("\n\n", "\n")

    try:
        key_points = key_points.split("**Key Points**:")[1]
        key_points = "\n".join(line.lstrip() for line in key_points.splitlines())
    except:
        key_points = key_points.split("Key Points:")[-1]
        key_points = "\n".join(line.lstrip() for line in key_points.splitlines())
    
    tasks = [judge_image(task, image_path, key_points, model) for image_path in images_path]
    image_responses = await asyncio.gather(*tasks)

    whole_content_img = []
    whole_thoughts = []
    record = []
    pattern = r"[1-5]"
    for response, image_path in zip(image_responses, images_path):
        try:
            score_text = response.split("Score")[1]
            thought = response.split("**Reasoning**:")[-1].strip().lstrip("\n").split("\n\n")[0].replace('\n',' ')
            score = re.findall(pattern, score_text)[0]
            record.append({"Response": response, "Score": int(score)})
        except Exception as e:
            print(f"Error processing response: {e}")
            score = 0
            record.append({"Response": response, "Score": 0})

        if int(score) >= score_threshold:
            jpg_base64_str = encode_image(Image.open(image_path))
            whole_content_img.append(
                {
                    'type': 'image_url',
                    'image_url': {"url": f"data:image/png;base64,{jpg_base64_str}", "detail": "high"}
                }
            )
            if thought != "":
                whole_thoughts.append(thought)

    whole_content_img = whole_content_img[:MAX_IMAGE]
    whole_thoughts = whole_thoughts[:MAX_IMAGE]
    if len(whole_content_img) == 0:
        prompt = """User Task: {task}

Key Points: {key_points}

Action History:
{last_actions}"""
    text = prompt.format(task=task, last_actions="\n".join(f"{i+1}. {action}" for i, action in enumerate(last_actions)), key_points=key_points, thoughts = "\n".join(f"{i+1}. {thought}" for i, thought in enumerate(whole_thoughts)))

    messages = [
        {"role": "system", "content": system_msg},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text}]
                + whole_content_img
        }
    ]
    return messages, text, system_msg, record, key_points
