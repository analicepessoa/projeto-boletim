(() => {
  "use strict";

  const BUTTON_ID = "allnet-boletins-importador";
  const MODAL_ID = "allnet-boletins-modal";
  const FORMAT = "allnet-boletins/v1";
  if (document.getElementById(BUTTON_ID)) return;

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const clean = (value) => String(value ?? "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
  const normalize = (value) => clean(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  const visible = (element) => Boolean(
    element && (element.offsetWidth || element.offsetHeight || element.getClientRects().length)
  );

  function labelOf(input) {
    if (!input) return "";
    const label = document.querySelector(`label[for="${input.id}"]`);
    return clean(label?.innerText || input.parentElement?.innerText || "");
  }

  function visibleAcademicTable() {
    return [...document.querySelectorAll("table.react-table, table")].find((table) => {
      if (!visible(table)) return false;
      const headers = [...table.querySelectorAll("thead th")].map((cell) => normalize(cell.innerText));
      return headers[0]?.includes("matricula") && headers[1]?.includes("nome");
    });
  }

  function tableSignature() {
    const table = visibleAcademicTable();
    if (!table) return "";
    return clean(table.innerText);
  }

  function hasVisibleEmptyState() {
    const emptyPattern = /nenhum registro|nenhum resultado|nenhum dado|não há dados|nao ha dados|sem dados|nenhuma aula|nenhuma prova/i;
    return [...document.querySelectorAll("p, span, td, div")].some((element) => {
      if (!visible(element) || element.children.length > 2) return false;
      const text = clean(element.innerText);
      return text.length > 0 && text.length < 180 && emptyPattern.test(text);
    });
  }

  function parseNumber(value) {
    const match = clean(value).replace(",", ".").match(/-?\d+(?:\.\d+)?/);
    if (!match) return null;
    const number = Number(match[0]);
    return Number.isFinite(number) ? number : null;
  }

  function readAcademicTable() {
    const table = visibleAcademicTable();
    if (!table) throw new Error("A tabela de alunos não apareceu.");

    const headers = [...table.querySelectorAll("thead th")].map((cell) => clean(cell.innerText));
    const attendanceIndexes = [];
    const gradeIndexes = [];
    headers.forEach((header, index) => {
      if (index < 2) return;
      if (normalize(header).startsWith("aula")) attendanceIndexes.push(index);
      else gradeIndexes.push(index);
    });

    const students = [...table.querySelectorAll("tbody tr")].map((row) => {
      const cells = [...row.querySelectorAll("td")].map((cell) => clean(cell.innerText));
      const ctr = cells[0] || "";
      const name = cells[1] || "";
      if (!ctr || !name) return null;

      const detailedGrades = {};
      const numericGrades = [];
      let preferredGrade = null;
      gradeIndexes.forEach((index) => {
        const number = parseNumber(cells[index]);
        if (number === null) return;
        detailedGrades[headers[index] || `Avaliação ${index - 1}`] = number;
        numericGrades.push(number);
        if (/media|média|nota final/i.test(headers[index])) preferredGrade = number;
      });

      const frequency = attendanceIndexes.map((index) => clean(cells[index]).toUpperCase().slice(0, 1));
      const presences = frequency.filter((status) => status === "P").length;
      const absences = frequency.filter((status) => status === "F").length;
      const grade = preferredGrade ?? (
        numericGrades.length
          ? numericGrades.reduce((sum, number) => sum + number, 0) / numericGrades.length
          : 0
      );

      return {
        ctr,
        nome: name,
        nota: Math.round(grade * 100) / 100,
        presencas: presences,
        faltas: absences,
        frequencia_detalhada: frequency,
        notas_detalhadas: detailedGrades,
      };
    }).filter(Boolean);

    return { colunas: headers, alunos: students };
  }

  async function searchAndWait(previousSignature) {
    let searchButton = [...document.querySelectorAll('button[title="Pesquisar"]')].find(visible);
    if (!searchButton) {
      const filtersButton = [...document.querySelectorAll("button")].find(
        (button) => visible(button) && normalize(button.innerText).includes("filtros")
      );
      filtersButton?.click();
      await sleep(250);
      searchButton = [...document.querySelectorAll('button[title="Pesquisar"]')].find(visible);
    }
    searchButton ||= document.querySelector('button[title="Pesquisar"]');
    if (!searchButton) throw new Error("O botão Pesquisar não foi encontrado.");

    searchButton.click();
    await sleep(500);
    const startedAt = Date.now();
    let stableCount = 0;
    let lastSignature = "";
    let sawTransition = false;
    const deadline = startedAt + 15000;
    while (Date.now() < deadline) {
      const signature = tableSignature();
      const elapsed = Date.now() - startedAt;
      if (!signature || signature !== previousSignature) sawTransition = true;
      if (signature && signature === lastSignature) stableCount += 1;
      else stableCount = 0;
      lastSignature = signature;
      if (!signature && elapsed >= 1000 && hasVisibleEmptyState()) {
        return "empty";
      }
      if (signature && stableCount >= 3 && (sawTransition || elapsed >= 5000)) {
        return "table";
      }
      if (!signature && elapsed >= 8000) {
        return "empty";
      }
      await sleep(250);
    }
    return visibleAcademicTable() ? "table" : "empty";
  }

  function downloadPackage(data) {
    const safeClass = clean(data.turma.nome).replace(/[^a-z0-9_-]+/gi, "-").replace(/^-|-$/g, "");
    const date = new Date().toISOString().slice(0, 10);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ALLNET_${safeClass || "turma"}_${date}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  function setStatus(text, kind = "normal") {
    const status = document.querySelector(`#${MODAL_ID} [data-import-status]`);
    if (!status) return;
    status.textContent = text;
    status.dataset.kind = kind;
  }

  async function collectAll(startButton, closeButton) {
    const selectedClass = document.querySelector('input[name="idTurma"]:checked');
    const products = [...document.querySelectorAll('input[type="radio"][name="idProduto"]')]
      .filter((input) => input.value && labelOf(input));
    const originalProduct = document.querySelector('input[name="idProduto"]:checked');
    if (!selectedClass || !products.length) {
      setStatus("Selecione a turma e uma disciplina, pesquise e tente novamente.", "error");
      return;
    }

    startButton.disabled = true;
    closeButton.disabled = true;
    const modules = [];
    const ignoredModules = [];
    try {
      for (let index = 0; index < products.length; index += 1) {
        const product = products[index];
        const moduleName = labelOf(product);
        setStatus(`Coletando ${index + 1} de ${products.length}: ${moduleName}`);
        const previousSignature = tableSignature();
        product.click();
        await sleep(100);
        if (!product.checked) throw new Error(`Não foi possível selecionar ${moduleName}.`);
        const searchResult = await searchAndWait(previousSignature);
        const tableData = searchResult === "table" ? readAcademicTable() : null;
        if (!tableData || tableData.colunas.length <= 2 || tableData.alunos.length === 0) {
          ignoredModules.push({
            id: product.value,
            nome: moduleName,
            motivo: "Módulo ainda sem aulas, provas ou alunos cadastrados",
          });
          continue;
        }
        modules.push({ id: product.value, nome: moduleName, ...tableData });
      }

      if (!modules.length) {
        throw new Error("Nenhum módulo com conteúdo acadêmico foi encontrado nesta turma.");
      }

      const data = {
        formato: FORMAT,
        criado_em: new Date().toISOString(),
        origem: location.origin + location.pathname,
        turma: { id: selectedClass.value, nome: labelOf(selectedClass) },
        modulos: modules,
        modulos_ignorados: ignoredModules,
      };
      downloadPackage(data);
      const ignoredText = ignoredModules.length
        ? ` ${ignoredModules.length} módulo(s) ainda vazio(s) foram ignorados.`
        : "";
      setStatus(
        `Pronto: ${modules.length} módulos e ${modules.reduce((sum, item) => sum + item.alunos.length, 0)} registros reunidos.${ignoredText} Agora envie o arquivo no Sistema de Boletins.`,
        "success"
      );
    } catch (error) {
      console.error("Importador ALLNET:", error);
      setStatus(`Não foi possível concluir: ${error.message}`, "error");
    } finally {
      if (originalProduct && !originalProduct.checked) {
        originalProduct.click();
        try { await searchAndWait(tableSignature()); } catch (_) { /* mantém o pacote já gerado */ }
      }
      startButton.disabled = false;
      closeButton.disabled = false;
    }
  }

  function openModal() {
    document.getElementById(MODAL_ID)?.remove();
    const selectedClass = document.querySelector('input[name="idTurma"]:checked');
    const products = [...document.querySelectorAll('input[type="radio"][name="idProduto"]')]
      .filter((input) => input.value && labelOf(input));

    const overlay = document.createElement("div");
    overlay.id = MODAL_ID;
    overlay.innerHTML = `
      <div class="allnet-import-card" role="dialog" aria-modal="true" aria-label="Importador ALLNET">
        <h2>Importador ALLNET</h2>
        <p>Turma encontrada: <strong>${labelOf(selectedClass) || "nenhuma"}</strong></p>
        <p>Módulos encontrados: <strong>${products.length}</strong></p>
        <p class="allnet-import-note">A coleta acontece apenas nesta página. Sua senha não é lida nem enviada.</p>
        <div data-import-status data-kind="normal">A ALLNET trocará os módulos automaticamente. Não mexa na página durante a coleta.</div>
        <div class="allnet-import-actions">
          <button type="button" data-close>Fechar</button>
          <button type="button" data-start>Reunir todos os módulos</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    const closeButton = overlay.querySelector("[data-close]");
    const startButton = overlay.querySelector("[data-start]");
    closeButton.addEventListener("click", () => overlay.remove());
    startButton.addEventListener("click", () => collectAll(startButton, closeButton));
  }

  const style = document.createElement("style");
  style.textContent = `
    #${BUTTON_ID} { position: fixed; right: 22px; bottom: 22px; z-index: 2147483000; border: 0; border-radius: 12px; padding: 13px 18px; background: #2563eb; color: #fff; font: 700 14px system-ui, sans-serif; box-shadow: 0 8px 28px rgba(15,23,42,.25); cursor: pointer; }
    #${BUTTON_ID}:hover { background: #1d4ed8; }
    #${MODAL_ID} { position: fixed; inset: 0; z-index: 2147483640; display: grid; place-items: center; background: rgba(15,23,42,.58); font-family: system-ui, sans-serif; }
    #${MODAL_ID} .allnet-import-card { width: min(520px, calc(100vw - 32px)); box-sizing: border-box; border-radius: 16px; padding: 24px; background: #fff; color: #0f172a; box-shadow: 0 24px 80px rgba(0,0,0,.3); }
    #${MODAL_ID} h2 { margin: 0 0 16px; font-size: 24px; }
    #${MODAL_ID} p { margin: 8px 0; }
    #${MODAL_ID} .allnet-import-note { color: #475569; }
    #${MODAL_ID} [data-import-status] { margin-top: 16px; border-radius: 10px; padding: 12px; background: #eff6ff; color: #1e3a8a; }
    #${MODAL_ID} [data-import-status][data-kind="success"] { background: #ecfdf5; color: #166534; }
    #${MODAL_ID} [data-import-status][data-kind="error"] { background: #fef2f2; color: #991b1b; }
    #${MODAL_ID} .allnet-import-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
    #${MODAL_ID} button { border: 0; border-radius: 9px; padding: 10px 14px; font-weight: 700; cursor: pointer; }
    #${MODAL_ID} button[data-close] { background: #e2e8f0; color: #0f172a; }
    #${MODAL_ID} button[data-start] { background: #2563eb; color: #fff; }
    #${MODAL_ID} button:disabled { opacity: .55; cursor: wait; }
  `;
  document.documentElement.appendChild(style);

  const button = document.createElement("button");
  button.id = BUTTON_ID;
  button.type = "button";
  button.textContent = "Enviar para Boletins";
  button.addEventListener("click", openModal);
  document.body.appendChild(button);
})();

