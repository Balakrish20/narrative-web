import pandas as pd
from datetime import datetime
from dateutil import parser
import inflect

# Initialize inflect engine for proper grammar
p = inflect.engine()

def get_value_or_default(val, default="unknown"):
    """Get value or return default if value is NaN, empty, or whitespace-only"""
    return default if pd.isna(val) or str(val).strip() == "" else str(val).strip()

def join_items(lst):
    """Join list items with proper grammar (commas and 'and')"""
    lst = [i for i in lst if i]
    if len(lst) == 1: 
        return lst[0]
    elif len(lst) == 2: 
        return f"{lst[0]} and {lst[1]}"
    elif len(lst) > 2: 
        return ", ".join(lst[:-1]) + f", and {lst[-1]}"
    return ""

def build_narrative(group):
    """Build narrative from grouped regulatory data"""
    row = group.iloc[0]
    
    # Extract basic case information
    regulatory_ID = get_value_or_default(row.get("regulatory_ID"))
    case_justification = get_value_or_default(row.get("case_justification"))
    case_type = get_value_or_default(row.get("case_type"))
    reporter = get_value_or_default(row.get("reporter_type")).lower()
    title = get_value_or_default(row.get("publication_title"))
    country = get_value_or_default(row.get("country"))
    ird = get_value_or_default(row.get("IRD"))

    # Format IRD date
    try:
        ird_fmt = parser.parse(ird).strftime("%d-%b-%Y").upper()
    except:
        ird_fmt = "unknown"

    # Process suspect drugs
    suspect_list = group["suspect_drug"].dropna().unique().tolist()
    suspect_text = join_items(suspect_list) if suspect_list else "(no suspect drugs listed)"
    manufacturer_text = "(unknown manufacturer)" if len(suspect_list) <= 1 else "(unknown manufacturers)"
    cosuspect = get_value_or_default(row.get("co_suspect_drug"))
    event = get_value_or_default(row.get("event"))

    # ------- Age & Gender Formatting with 'a/an' -------
    age_raw = get_value_or_default(row.get("age"), "")
    gender_raw = get_value_or_default(row.get("gender"), "")
    age_known = age_raw.lower() not in ["", "unknown", "nan"]
    gender_known = gender_raw.lower() not in ["", "unknown", "nan"]

    try:
        age_int = int(float(age_raw))
        age_phrase = f"{p.a(f'{age_int}-year-old')}"
    except:
        age_phrase = ""

    if age_known and gender_known:
        patient_description = f"{age_phrase} {gender_raw.lower()} patient"
    elif age_known and not gender_known:
        patient_description = f"{age_phrase} patient (unknown gender)"
    elif not age_known and gender_known:
        patient_description = f"{p.a(gender_raw.lower())} patient (unknown age)"
    else:
        patient_description = "patient (unknown demographics)"

    # Paragraph 1 - Case Overview
    p1 = f"This {case_justification} case was reported by a {reporter} with medical literature {title}, from {country}. "
    p1 += f"This case was received by Alkem on {ird_fmt} from {case_type} with {regulatory_ID}. "
    p1 += f"It concerns {patient_description}, who was administered {suspect_text} {manufacturer_text}. "
    p1 += f"The co-suspect drug was {cosuspect}. The patient experienced {event}."

    # Paragraph 2 — Structured Rule-Based Patient History
    fields = {
        "medical history": group["medical_history"],
        "past drug therapy": group["past_drug_therapy"],
        "concurrent conditions": group["concurrent_condition"],
        "concomitant medications": group["concomitant_medication"]
    }

    para2_parts = []
    not_reported = []

    for label, series in fields.items():
        values = [get_value_or_default(val) for val in series if get_value_or_default(val) != "unknown"]
        if values:
            phrase_label = label if len(values) > 1 else label.rstrip("s")
            para2_parts.append(f"{phrase_label} included {join_items(values)}")
        else:
            not_reported.append(label)

    if para2_parts:
        p2 = f"The patient's {'. '.join(para2_parts)}."
    else:
        p2 = ""

    if not_reported:
        missing_info = f"The {join_items(not_reported)} were not reported."
        p2 = f"{p2} {missing_info}".strip()

    # Paragraph 3 - Drug Administration Details
    drug_lines = []
    for _, r in group.iterrows():
        date = get_value_or_default(r.get("suspect_drug_start_date"))
        try:
            date_fmt = parser.parse(date).strftime("%d-%b-%Y").upper()
        except:
            date_fmt = "unknown date"
        drug = get_value_or_default(r.get("suspect_drug"))
        dose = get_value_or_default(r.get("dose"))
        freq = get_value_or_default(r.get("frequency"))
        route = get_value_or_default(r.get("route"))
        indication = get_value_or_default(r.get("indication"), "an unknown indication")
        line = f"On {date_fmt}, the patient was administered {drug} at the dose of {dose}, frequency {freq}, via {route} for {indication}."
        drug_lines.append(line)

    if len(drug_lines) == 1:
        drug_lines.append("The batch number and expiration date were not reported.")
    elif len(drug_lines) > 1:
        drug_lines.append("The batch numbers and expiration dates were not reported.")

    p3 = " ".join(drug_lines)
    return f"{p1}\n\n{p2}\n\n{p3}"
