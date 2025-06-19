async function generateNarratives() {
  const inputText = document.getElementById("inputArea").value;
  const rows = inputText.trim().split("\n").map(row => row.split("\t"));
  const headers = rows[0];
  const data = rows.slice(1).map(row => {
    const obj = {};
    headers.forEach((col, i) => obj[col] = row[i] || "");
    return obj;
  });

  const response = await fetch('/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data })
  });

  const result = await response.json();
  const outputDiv = document.getElementById("outputArea");
  outputDiv.innerHTML = '';

  if (Array.isArray(result)) {
    result.forEach(entry => {
      outputDiv.innerHTML += `<h4>ID: ${entry.regulatory_ID}</h4><pre>${entry.narrative}</pre><hr>`;
    });
  } else {
    outputDiv.innerHTML = `<p style="color:red;">Error: ${result.error}</p>`;
  }
}
