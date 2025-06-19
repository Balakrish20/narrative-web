import pandas as pd
from dateutil import parser
import inflect

p = inflect.engine()

def get_value_or_default(val, default="unknown"):
    return default if pd.isna(val) or str(val).strip() == "" else str(val).strip()

def join_items(lst):
    lst = [i for i in lst if i]
    if len(lst) == 1: return lst[0]
    elif len(lst) == 2: return f"{lst[0]} and {lst[1]}"
    elif len(lst) > 2: return ", ".join(lst[:-1]) + f", and {lst[-1]}"
    return ""

def build_narrative(group):
    row = group.iloc[0]
    regulatory_ID = get_value_or_default(row.get("regulatory_ID"))
    case_justification = get_value_or_default(row.get("case_justification"))
    case_type = get_value_or_default(row.get("case_type"))
    return f"Case {regulatory_ID}: A {case_type} case with justification '{case_justification}'."
    row = group.iloc[0]
    reporter = get_value_or_default(row.get("reporter_type")).lower()
    title = get_value_or_default(row.get("publication_title"))
    country = get_value_or_default(row.get("country"))
    ird = get_value_or_default(row.get("IRD"))

    try:
        ird_fmt = parser.parse(ird).strftime("%d-%b-%Y").upper()
    except:
        ird_fmt = "unknown"

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

    # Paragraph 1
    p1 = f"This {case_justification} case was reported by a {reporter} with medical literature \u201c{title}\u201d, from {country}. "
    p1 += f"This case was received by Alkem on {ird_fmt} from {case_type} with {regulatory_ID}. "
    p1 += f"It concerns {patient_description}, who was administered {suspect_text} {manufacturer_text}. "
    p1 += f"The co-suspect drug was {cosuspect}. The patient experienced {event}."

    # Paragraph 2
        # Paragraph 2 — Structured Rule-Based
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
        p2 = f"The patient’s {'. '.join(para2_parts)}."
    else:
        p2 = ""

    if not_reported:
        missing_info = f"The {join_items(not_reported)} were not reported."
        p2 = f"{p2} {missing_info}".strip()

    # Paragraph 3
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

# ---------- UI Layout ----------
columns = [
    "regulatory_ID", "case_justification", "case_type", "reporter_type", "publication_title", "country", "IRD",
    "age", "gender", "suspect_drug", "co_suspect_drug", "event", "medical_history", "past_drug_therapy",
    "concurrent_condition", "concomitant_medication", "dose", "frequency", "route", "indication",
    "suspect_drug_start_date"
]

notebook = ttk.Notebook(root)
tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)
notebook.add(tab1, text='Tabular Input')
notebook.add(tab2, text='Narrative Output')
notebook.pack(fill='both', expand=True)

# Tab 1 - Table Input
tree_frame = ttk.Frame(tab1)
tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
tree_scroll_x = tk.Scrollbar(tree_frame, orient='horizontal')
tree_scroll_y = tk.Scrollbar(tree_frame, orient='vertical')
tree_scroll_x.pack(side='bottom', fill='x')
tree_scroll_y.pack(side='right', fill='y')

tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                    xscrollcommand=tree_scroll_x.set, yscrollcommand=tree_scroll_y.set)
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=120, anchor='w')
tree.pack(fill='both', expand=True)
tree_scroll_x.config(command=tree.xview)
tree_scroll_y.config(command=tree.yview)

# Buttons
btn_frame = ttk.Frame(tab1)
btn_frame.pack(pady=5)

def paste_data():
    try:
        clipboard = root.clipboard_get()
        rows = [row.split('\t') for row in clipboard.strip().split('\n')]
        for row in rows:
            row += [""] * (len(columns) - len(row))
            tree.insert("", "end", values=row[:len(columns)])
    except Exception as e:
        messagebox.showerror("Paste Error", str(e))

def generate_narratives_from_grid():
    try:
        data = [tree.item(child)["values"] for child in tree.get_children()]
        if not data:
            messagebox.showwarning("Empty", "No data available.")
            return
        df = pd.DataFrame(data, columns=columns)
        grouped = df.groupby("regulatory_ID")
        results = []
        for reg_id, group in grouped:
            narrative = build_narrative(group)
            results.append({"regulatory_ID": reg_id, "Narrative": narrative})
        result_df = pd.DataFrame(results)
        narrative_output.config(state='normal')
        narrative_output.delete("1.0", tk.END)
        for _, row in result_df.iterrows():
            narrative_output.insert(tk.END, f"ID: {row['regulatory_ID']}\n{row['Narrative']}\n\n{'-'*60}\n")
        narrative_output.config(state='disabled')
    except Exception as e:
        messagebox.showerror("Generation Error", str(e))

ttk.Button(btn_frame, text="Paste from Clipboard", command=paste_data).pack(side='left', padx=5)
ttk.Button(btn_frame, text="Generate Narratives", command=generate_narratives_from_grid).pack(side='left', padx=5)
ttk.Button(btn_frame, text="Clear Table", command=lambda: tree.delete(*tree.get_children())).pack(side='left', padx=5)

# Tab 2 - Output
output_frame = ttk.Frame(tab2)
output_frame.pack(fill='both', expand=True, padx=5, pady=5)
output_scroll = tk.Scrollbar(output_frame)
output_scroll.pack(side='right', fill='y')
narrative_output = tk.Text(output_frame, wrap='word', yscrollcommand=output_scroll.set,
                           font=('Segoe UI', 10), state='disabled')
narrative_output.pack(side='left', fill='both', expand=True)
output_scroll.config(command=narrative_output.yview)

root.mainloop()
