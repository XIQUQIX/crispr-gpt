PROMPT_REQUEST_EASY = """
In order to complete the current task, we would need you to answer the following questions. 

If you are not sure how to select, we recommend you use the Meta-mode where we could generate case-specific guidance based on your needs, please open a new chat and enter meta-mode (select option 1 for the initial prompt).

1. Which Cas system are you planning to use? (We currently support SpCas9, enCas12a, SaCas9, SpRYCas9)
"""

PROMPT_PROCESS_EASY = """Please act as an expert in CRISPR technology. Given the instruction and user input, think step by step and give the response. Please format your response following response format and make sure it is parsable by JSON.

Instruction:

Given the user input, identify the single most relevant Cas system below.

1. SpCas9 (from Streptococcus pyogenes)
Pros:
High efficiency in a wide range of organisms.
Extensive research and documentation available.
Cons:
Large protein size can complicate delivery mechanisms.
Potential for off-target effects.
Applications:
Broad, including basic genetic research, gene therapy, and development of genetically modified organisms (GMOs).

2. enCas12a (engineered Cas12a variant)
Pros:
Smaller than SpCas9, allowing for easier delivery in certain vectors.
Generates staggered DNA double-strand breaks, potentially facilitating precise genome editing.
Has a lower off-target rate, offering increased genome editing fidelity.
Unique ability to simultaneously cut multiple sites, allowing for the efficient targeting and editing of several genomic locations in a single experiment.
Cons:
Sometimes exhibits lower editing efficiency compared to SpCas9.
Requires distinct PAM sequences, which might limit target sites.
Applications:
Ideal for applications requiring higher precision, reduced off-target and multiplexed editing, like therapeutic gene editing and complex genome engineering tasks.

3. SaCas9 (from Staphylococcus aureus)
Pros:
More compact than SpCas9, enhancing its suitability for certain delivery methods such as AAV vectors.
Cons:
Limited by a narrower PAM compatibility, restricting its targeting scope.
Applications:
Primarily used in in vivo therapeutic applications where delivery vector size is a limiting factor, such as gene therapy for inherited genetic disorders.

4. SpRYCas9 (engineered variant of SpCas9)
Pros:
Broadened PAM recognition, greatly expanding genomic targeting capabilities.
Cons:
Increased potential for off-target effects due to broader specificity.
Applications:
Suitable for complex genome editing applications targeting genomic regions previously inaccessible, including research and therapeutic contexts where high specificity is not as critical.

User Input:

{user_message}

Response format:
{{
"Thoughts": "<thoughts>", # Think step by step to figure out which Cas system is most relevant to user's input.
"Answer": "<answer>" # Choose the single most relevant Cas system. Don't put additional words here. Only put a single name (SpCas9, enCas12a, SaCas9, SpRYCas9).
}}"""



PROMPT_REQUEST_ENTRY = """Now, let's start designing and planning your knockout experiment using CRISPR system, we will go through a step by step process as listed below:
1. Selecting a CRISPR/Cas system.
2. Selecting a delivery approach for CRISPR/Cas system. (content pending in Lite version)
3. Designing guideRNA for gene knockout.
4. Collecting appropriate experimental protocols. (content pending in Lite version)
5. Validating the editing outcomes and designing sequencing primers. (content pending in Lite version)
"""

PROMPT_STEP1 = """
Step 1. Selecting a CRISPR/Cas system 

We support four types of CRISPR/Cas system for CRISPR knockout, SpCas9, enCas12a, SaCas9, and SpRYCas9, representing distinct variants with unique properties and applications.

1. SpCas9  (Jinek et al.,Science,2012;Cong et al.,Science,2013;Mali et al.,Science,2013;Jinek et al.,eLife,2013)
- Pros: Highly effective, well-studied, proven applications in many cell types/scenarios.  
- Cons: Large, potential off-target effects.  
- Uses: Genetic research, gene therapy, genetically modified models/organisms (GMMs/GMOs).

2. enCas12a  (Kleinstiver et al.,Nat Biotechnol.,2019;DeWeirdt et al.,Nat Biotechnol.,2020)
- Pros: Smaller, precise, low off-target rate, multi-target editing capability using a single guideRNA array.  
- Cons: May be less efficient than SpCas9 when using a single guideRNA (mitigated if using multi-guide array), limited target sites vs. SpCas9 due to more restrictive PAM.  
- Uses: High-precision and multiplexed genome editing (for genetic interaction, target redundant genes/pathways).

3. SaCas9  (Ran et al.,Nature,2015)
- Pros: Compact, suitable for AAV vectors (knockout genes in primary cells or in vivo).  
- Cons: limited target sites vs. SpCas9 due to more restrictive PAM.  
- Uses: In vivo gene therapy and some primary cells when using AAV delivery.

4. SpRYCas9  (Walton et al.,Science,2020)
- Pros: Wide PAM range, targets more genomic regions vs. typical SpCas9.  
- Cons: Higher off-target risks.  
- Uses: editing a specific target site where canonical PAMs for SpCas9/SaCas9/enCas12a are not available, and where specificity/off-target concerns are less critical.

*Please cite the corresponding papers if you decide to use the system.
"""

PROMPT_REQUEST_STEP1_INQUIRY = """
Please select the CRISPR-Cas system you would like to use. Or please briefly describe your need (exp: I want to edit mouse liver/I want low off-target rate/I want to do multiplexed editing) and we could recommend the CRSIPR-Cas system to you.
"""

PROMPT_PROCESS_STEP1_INQUIRY = """Please act as an expert in CRISPR technology. Given the instruction and user input, think step by step and give the response. Please format your response following response format and make sure it is parsable by JSON.

Instruction:

Given the user input, identify the single most relevant Cas system below.

1. SpCas9 (from Streptococcus pyogenes)
Pros:
High efficiency in a wide range of organisms.
Extensive research and documentation available.
Cons:
Large protein size can complicate delivery mechanisms.
Potential for off-target effects.
Applications:
Broad, including basic genetic research, gene therapy, and development of genetically modified organisms (GMOs).

2. enCas12a (engineered Cas12a variant)
Pros:
Smaller than SpCas9, allowing for easier delivery in certain vectors.
Generates staggered DNA double-strand breaks, potentially facilitating precise genome editing.
Has a lower off-target rate, offering increased genome editing fidelity.
Unique ability to simultaneously cut multiple sites, allowing for the efficient targeting and editing of several genomic locations in a single experiment.
Cons:
Sometimes exhibits lower editing efficiency compared to SpCas9.
Requires distinct PAM sequences, which might limit target sites.
Applications:
Ideal for applications requiring higher precision, reduced off-target and multiplexed editing, like therapeutic gene editing and complex genome engineering tasks.

3. SaCas9 (from Staphylococcus aureus)
Pros:
More compact than SpCas9, enhancing its suitability for certain delivery methods such as AAV vectors.
Cons:
Limited by a narrower PAM compatibility, restricting its targeting scope.
Applications:
Primarily used in in vivo therapeutic applications where delivery vector size is a limiting factor, such as gene therapy for inherited genetic disorders.

4. SpRYCas9 (engineered variant of SpCas9)
Pros:
Broadened PAM recognition, greatly expanding genomic targeting capabilities.
Cons:
Increased potential for off-target effects due to broader specificity.
Applications:
Suitable for complex genome editing applications targeting genomic regions previously inaccessible, including research and therapeutic contexts where high specificity is not as critical.

User Input:

{user_message}

Response format:
{{
"Thoughts": "<thoughts>", # Think step by step to figure out which Cas system is most relevant to user's input.
"Answer": "<answer>" # Choose the single most relevant Cas system. Don't put additional words here. Only put a single name (SpCas9, enCas12a, SaCas9, SpRYCas9).
}}"""


PROMPT_REQUEST_STEP3="""
Step 3. Designing guideRNA for gene knockout

Next, we would like to guide you through the design of guideRNA for your target gene. Designing an effective and specific single-guide RNA (sgRNA) is crucial for successful CRISPR/Cas9-mediated genome editing.There are several factors to consider in this process, including the selection of target sites that are unique to your gene of interest and minimizing potential off-target effects. 

"""
 
 