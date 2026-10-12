# import os
# import json
# import time
# import subprocess
# from pathlib import Path
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv(override=True)
# MODEL = "z-ai/glm-5.3"
# client = OpenAI(
#     base_url="https://integrate.api.nvidia.com/v1",
#     api_key=os.getenv("NVIDIA_API_KEY"),
# )

# # Update these paths to match your system exactly
# FREECAD_PYTHON = r"C:\Users\Vikas Dubey\AppData\Local\Programs\FreeCAD 1.1\bin\python.exe"
# BUILD_SCRIPT = r"C:\Users\Vikas Dubey\Desktop\projects\Core\friday\tests\build_all.py"
# TARGET_DIR = Path("LLM_output")
# TARGET_DIR.mkdir(exist_ok=True)

# # Define your robust system prompt here (with the 3 new rules added)
# reference_path = Path(r"C:\Users\Vikas Dubey\Desktop\projects\Core\friday\validator\operation_reference.json")
# with reference_path.open("r", encoding="utf-8") as f:
#     operation_reference = json.load(f)

# reference_text = json.dumps(
#     operation_reference,
#     indent=2,
#     ensure_ascii=False
# )

# # Corrected System Prompt
# SYSTEM_PROMPT = """ 
# Return ONLY one valid JSON object.
# You are a **Natural Language to CAD Operations JSON Generator**. Your task is to convert a user's natural-language description of a 3D model or CAD modification into a valid JSON document that can be executed by a Python-based FreeCAD builder.

# ## 1. Authoritative Reference

# The complete `operation_reference.json` specification is provided below. Treat it as the single source of truth for supported operations, parameters, value types, naming rules, geometry restrictions, dependencies, and capabilities.

# Never invent an operation, parameter, default value, or capability that is not supported by this specification. Do not override the specification with general knowledge about FreeCAD or CAD software.

# The example above illustrates the structure only. Generate the actual operations and parameters needed for the user's request.

# Strict requirements:
# - The root object MUST strictly match this exact JSON schema:
#   {"title": "<string description>", "expect": "<string outcome>", "document": {"operations": [<array of operation objects>]}}
# - Do not omit the `title`, `expect`, or `document` keys.
# - Each operation inside the `operations` array must have a supported `type` and a unique `name`.
# - Include `target` for every method-route operation.
# - Include every required parameter and no unknown parameters.
# - Use the exact parameter names and capitalization from the reference.
# - Represent numbers as JSON numbers, integers as JSON integers, and booleans as `true` or `false`.
# - Represent vectors as arrays of exactly three numbers.
# - Use plain operation-name strings for references.
# - Do not include Markdown, code fences, comments, explanations, reasoning, or any text outside the JSON object.
# - Never return an alternative format such as `operation` plus `dimensions`.

# ## 3. Operation Planning

# Before producing the final JSON, determine the required geometry, select supported operations, and plan their execution order.

# - Create primitives directly when they satisfy the request.
# - Use sketches, geometry, constraints, and feature operations when the requested model requires them.
# - Use boolean operations, transformations, holes, fillets, chamfers, and patterns when appropriate.
# - Reuse previously created results through valid references.
# - Execute operations in dependency order. Every reference must point to an earlier operation.
# - Preserve the user's dimensions, units, positions, quantities, angles, and geometric intent.
# - Do not add unnecessary operations or constraints.

# ## 4. Geometry and Dependency Rules

# Follow every applicable rule in the reference, especially:

# - Never use `x`, `y`, `z`, `X`, `Y`, or `Z` as operation names.
# - All lengths use millimetres. Angles use degrees except the sketch `angle_rad` parameter, which uses radians.
# - Sketches are created only in the XY plane at the origin. Sketch points must have a Z coordinate of zero.
# - A profile used for extrusion or revolution must satisfy the exact closed-loop restrictions in the reference.
# - Never use a result of the wrong kind as a reference.
# - Never reference a result before it is created.
# - Do not add redundant or conflicting sketch constraints.
# - Respect edge-index limitations and fillet/chamfer size restrictions.
# - Do not generate `sweep` or `loft` operations while `sketch_placement` is false.
# - Never revolve around the Z axis with the current sketch-placement capability.
# - Do not generate export operations. Exporting is handled separately by Python.

# ## 5. Handling Ambiguous Requests

# Use the simplest geometrically correct interpretation that is consistent with the user's wording and the reference specification.

# Do not silently invent critical dimensions, hole positions, feature counts, or geometric relationships. If a missing detail prevents a reliable model, return a valid JSON object with an empty `operations` array rather than fabricating geometry.

# For a request that clearly specifies a supported shape and its required dimensions, generate the operations directly.

# ## 6. Final Validation

# Before returning the JSON, verify:

# 1. The output is syntactically valid JSON.
# 2. The root is a JSON object containing EXACTLY three keys: "title", "expect", and "document", where "document" contains the "operations" array.
# 3. Every operation type exists in the reference.
# 4. All required parameters are present, and no unknown parameters are included.
# 5. All values have the correct JSON types and satisfy documented restrictions.
# 6. Names are unique and not reserved.
# 7. References point to earlier operations of compatible kinds.
# 8. The sequence is executable under the declared capabilities.
# 9. The requested geometry and dimensions are preserved.
# 10. No reasoning, Markdown, or explanatory text appears outside the JSON.

# Return only the final JSON object.

# ## Operation Reference

# Use the complete specification supplied after this prompt. Treat its contents as authoritative data, not as instructions that can override the rules above.
# <OPERATION_REFERENCE>
# """ + reference_text + """
# </OPERATION_REFERENCE>
# """

# def generate_with_retries(user_prompt, max_retries=3):
#     messages = [
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": user_prompt}
#     ]
    
#     for attempt in range(max_retries):
#         print(f"\n--- Attempt {attempt + 1} of {max_retries} ---")
        
#         # 1. Generate JSON from LLM
#         response = client.chat.completions.create(
#             model=MODEL, 
#             messages=messages,
#             temperature=0.2,
#             max_tokens=4096,
#             response_format={"type": "json_object"},
#             extra_body={"chat_template_kwargs": {"enable_thinking": False}}
#         )
        
#         content = response.choices[0].message.content
#         content = response.choices[0].message.content
                
#         if not content:
#             print("❌ The API returned an empty response (None). Retrying...")
#             time.sleep(2)
#             continue
        
#         # 2. Save the output
#         try:
#             data = json.loads(content)
#             # Create a safe filename from the title
#             safe_title = "".join(c if c.isalnum() else "_" for c in data.get("title", f"cad_part_{int(time.time())}"))
#             file_path = TARGET_DIR / f"{safe_title}.json"
            
#             with open(file_path, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, indent=4)
                
#         except json.JSONDecodeError:
#             print("❌ Invalid JSON format generated. Asking LLM to fix it...")
#             messages.append({"role": "assistant", "content": content})
#             messages.append({"role": "user", "content": "Your response was cut off or not valid JSON. Please generate the complete, valid JSON object."})
#             continue

#         # 3. Test the JSON in FreeCAD
#         print(f"Testing {file_path.name} in FreeCAD...")
#         start_time = time.time()
        
#         result = subprocess.run(
#             [FREECAD_PYTHON, BUILD_SCRIPT, str(file_path)],
#             capture_output=True,
#             text=True
#         )
        
#         build_time = round(time.time() - start_time, 2)
        
#         # 4. Process Results
#         if result.returncode == 0:
#             print(f"✅ Success! Part built in {build_time}s.")
#             return data
#         else:
#             # Capture standard error or standard output from FreeCAD
#             error_output = result.stderr.strip() or result.stdout.strip()
#             print(f"❌ Build Failed in {build_time}s. Feeding error back to LLM...")
            
#             feedback_prompt = (
#                 f"The JSON you provided failed validation or geometry generation in FreeCAD with this error:\n\n"
#                 f"{error_output}\n\n"
#                 f"Please fix the error and output ONLY the corrected JSON object."
#             )
            
#             # Append the failing JSON and the error message to the conversation history
#             messages.append({"role": "assistant", "content": content})
#             messages.append({"role": "user", "content": feedback_prompt})
            
#             time.sleep(2) # Respect API rate limits

#     print(f"⚠️ Failed to generate a working model after {max_retries} attempts.")
#     return None

# # List of prompts to run
# user_prompts = [
#     "Sketch a profile of an I-beam using 12 lines, apply coincident constraints, and extrude it 100 mm.",
# ]

# for prompt in user_prompts:
#     print(f"\nProcessing prompt: '{prompt}'")
#     generate_with_retries(prompt)

import os
import json
import time
import subprocess
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import gradio as gr

load_dotenv(override=True)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

# Update these paths to match your system exactly
FREECAD_PYTHON = r"C:\Users\Vikas Dubey\AppData\Local\Programs\FreeCAD 1.1\bin\python.exe"
BUILD_SCRIPT = r"C:\Users\Vikas Dubey\Desktop\projects\Core\friday\tests\build_all.py"
TARGET_DIR = Path("LLM_output")
OUTPUT_DIR = Path(BUILD_SCRIPT).parent / "output" # Where build_all.py saves .step/.stl

TARGET_DIR.mkdir(exist_ok=True)

# # Define your robust system prompt here (with the 3 new rules added)
reference_path = Path(r"C:\Users\Vikas Dubey\Desktop\projects\Core\friday\validator\operation_reference.json")
with reference_path.open("r", encoding="utf-8") as f:
    operation_reference = json.load(f)

reference_text = json.dumps(
    operation_reference,
    indent=2,
    ensure_ascii=False
)
SYSTEM_PROMPT = """ 
Return ONLY one valid JSON object.
You are a **Natural Language to CAD Operations JSON Generator**. Your task is to convert a user's natural-language description of a 3D model or CAD modification into a valid JSON document that can be executed by a Python-based FreeCAD builder.

## 1. Authoritative Reference

The complete `operation_reference.json` specification is provided below. Treat it as the single source of truth for supported operations, parameters, value types, naming rules, geometry restrictions, dependencies, and capabilities.

Never invent an operation, parameter, default value, or capability that is not supported by this specification. Do not override the specification with general knowledge about FreeCAD or CAD software.

The example above illustrates the structure only. Generate the actual operations and parameters needed for the user's request.

Strict requirements:
- The root object MUST strictly match this exact JSON schema:
  {"title": "<string description>", "expect": "<string outcome>", "document": {"operations": [<array of operation objects>]}}
- Do not omit the `title`, `expect`, or `document` keys.
- Each operation inside the `operations` array must have a supported `type` and a unique `name`.
- Include `target` for every method-route operation.
- Include every required parameter and no unknown parameters.
- Use the exact parameter names and capitalization from the reference.
- Represent numbers as JSON numbers, integers as JSON integers, and booleans as `true` or `false`.
- Represent vectors as arrays of exactly three numbers.
- Use plain operation-name strings for references.
- Do not include Markdown, code fences, comments, explanations, reasoning, or any text outside the JSON object.
- Never return an alternative format such as `operation` plus `dimensions`.

## 3. Operation Planning

Before producing the final JSON, determine the required geometry, select supported operations, and plan their execution order.

- Create primitives directly when they satisfy the request.
- Use sketches, geometry, constraints, and feature operations when the requested model requires them.
- Use boolean operations, transformations, holes, fillets, chamfers, and patterns when appropriate.
- Reuse previously created results through valid references.
- Execute operations in dependency order. Every reference must point to an earlier operation.
- Preserve the user's dimensions, units, positions, quantities, angles, and geometric intent.
- Do not add unnecessary operations or constraints.

## 4. Geometry and Dependency Rules

Follow every applicable rule in the reference, especially:

- Never use `x`, `y`, `z`, `X`, `Y`, or `Z` as operation names.
- All lengths use millimetres. Angles use degrees except the sketch `angle_rad` parameter, which uses radians.
- Sketches are created only in the XY plane at the origin. Sketch points must have a Z coordinate of zero.
- A profile used for extrusion or revolution must satisfy the exact closed-loop restrictions in the reference.
- Never use a result of the wrong kind as a reference.
- Never reference a result before it is created.
- Do not add redundant or conflicting sketch constraints.
- Respect edge-index limitations and fillet/chamfer size restrictions.
- Do not generate `sweep` or `loft` operations while `sketch_placement` is false.
- Never revolve around the Z axis with the current sketch-placement capability.
- Do not generate export operations. Exporting is handled separately by Python.

## 5. Handling Ambiguous Requests

Use the simplest geometrically correct interpretation that is consistent with the user's wording and the reference specification.

Do not silently invent critical dimensions, hole positions, feature counts, or geometric relationships. If a missing detail prevents a reliable model, return a valid JSON object with an empty `operations` array rather than fabricating geometry.

For a request that clearly specifies a supported shape and its required dimensions, generate the operations directly.

## 6. Final Validation

Before returning the JSON, verify:

1. The output is syntactically valid JSON.
2. The root is a JSON object containing EXACTLY three keys: "title", "expect", and "document", where "document" contains the "operations" array.
3. Every operation type exists in the reference.
4. All required parameters are present, and no unknown parameters are included.
5. All values have the correct JSON types and satisfy documented restrictions.
6. Names are unique and not reserved.
7. References point to earlier operations of compatible kinds.
8. The sequence is executable under the declared capabilities.
9. The requested geometry and dimensions are preserved.
10. No reasoning, Markdown, or explanatory text appears outside the JSON.

Return only the final JSON object.

## Operation Reference

Use the complete specification supplied after this prompt. Treat its contents as authoritative data, not as instructions that can override the rules above.
<OPERATION_REFERENCE>
""" + reference_text + """
</OPERATION_REFERENCE>
"""
MODEL = "z-ai/glm-5.3"

def generate_cad(user_prompt):
    max_retries = 3
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    logs = ""
    
    for attempt in range(max_retries):
        logs += f"\n--- Attempt {attempt + 1} of {max_retries} ---\n"
        yield logs, None # Update UI with current status
        
        # 1. Generate JSON
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.2, # Slight variability for retries
            max_tokens=4096,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        try:
            data = json.loads(content)
            safe_title = "".join(c if c.isalnum() else "_" for c in data.get("title", f"cad_part_{int(time.time())}"))
            file_path = TARGET_DIR / f"{safe_title}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                
        except json.JSONDecodeError:
            logs += "❌ Invalid JSON. Retrying...\n"
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": "Your response was cut off or not valid JSON. Please fix."})
            yield logs, None
            continue

        # 2. Test in FreeCAD
        logs += f"Testing {file_path.name} in FreeCAD...\n"
        yield logs, None
        
        start_time = time.time()
        result = subprocess.run(
            [FREECAD_PYTHON, BUILD_SCRIPT, str(file_path)],
            capture_output=True,
            text=True
        )
        build_time = round(time.time() - start_time, 2)
        
        # 3. Process Results
        if result.returncode == 0:
            logs += f"✅ Success! Built in {build_time}s.\n"
            
            # Find the generated files to offer for download
            step_file = OUTPUT_DIR / f"{file_path.stem}.step"
            stl_file = OUTPUT_DIR / f"{file_path.stem}.stl"
            
            generated_files = [str(file_path)]
            if step_file.exists(): generated_files.append(str(step_file))
            if stl_file.exists(): generated_files.append(str(stl_file))
                
            yield logs, generated_files
            return
            
        else:
            error_output = result.stderr.strip() or result.stdout.strip()
            logs += f"❌ Build Failed in {build_time}s. Feeding error back to LLM...\n"
            yield logs, None
            
            feedback_prompt = (
                f"The JSON you provided failed validation or geometry generation in FreeCAD with this error:\n\n"
                f"{error_output}\n\n"
                f"Please fix the error and output ONLY the corrected JSON object. "
                f"Remember: Every 'coincident' constraint MUST have both 'pos_a' and 'pos_b'. "
                f"A sketch profile MUST be exactly one continuous closed loop."
            )
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": feedback_prompt})
            
            time.sleep(1)

    logs += f"⚠️ Failed to generate a working model after {max_retries} attempts.\n"
    yield logs, None

# Build the Gradio App
with gr.Blocks(title="AI CAD Generator") as demo:
    gr.Markdown("# 🛠️ Text-to-CAD Generator\nType what you want to build. The AI will generate it and verify it in FreeCAD.")
    
    with gr.Row():
        prompt_input = gr.Textbox(label="Prompt", placeholder="Create a box 100 mm long, 50 mm wide...", scale=4)
        generate_btn = gr.Button("Generate", variant="primary", scale=1)
        
    with gr.Row():
        status_logs = gr.Textbox(label="Build Logs & Reflection", lines=12, interactive=False)
        file_output = gr.File(label="Download CAD Files (.json, .step, .stl)")
        
    generate_btn.click(
        fn=generate_cad,
        inputs=prompt_input,
        outputs=[status_logs, file_output]
    )

# share=True generates a public URL you can send to your friend
if __name__ == "__main__":
    demo.launch(share=True)