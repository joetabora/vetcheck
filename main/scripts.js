const chatContainer = document.getElementById("chatContainer");
const inputArea = document.getElementById("inputArea");
const currentInput = document.getElementById("currentInput");
const loading = document.getElementById("loading");
const results = document.getElementById("results");
const diagnosisResult = document.getElementById("diagnosisResult");
const urgentResult = document.getElementById("urgentResult");
const consultResult = document.getElementById("consultResult");
const homecareResult = document.getElementById("homecareResult");
const veterinaryResult = document.getElementById("veterinaryResult");
const editBtn = document.getElementById("editBtn");

const questions = [
  {
    text: `Hello! I'm here to help you understand your pet's symptoms. To assist you properly, I'll need some basic information about your pet and their condition.\n\nWhen you're ready, start by telling me what species your pet is.`,
    input: '<input type="text" class="form-control" id="species" name="species" required placeholder="Enter cat or dog">',
  },
  {
    text: 'What breed is your pet? <span class="info-icon" data-bs-toggle="tooltip" data-bs-placement="right" title="Breed information helps identify genetic predispositions and breed-specific health concerns.">ⓘ</span>',
    input: '<input type="text" class="form-control" id="breed" name="breed" placeholder="e.g., Golden Retriever, Persian, Mixed breed">',
  },
  {
    text: "How old is your pet?",
    input: '<input type="text" class="form-control" id="age" name="age" required placeholder="e.g., 3 years, 6 months, 8 weeks">',
  },
  {
    text: 'What\'s your pet\'s biological sex? <span class="info-icon" data-bs-toggle="tooltip" data-bs-placement="right" title="Biological sex is important for veterinary diagnosis as many conditions are sex-specific.">ⓘ</span>',
    input: '<select class="form-select" id="sex" name="sex" required><option value="">Select sex</option><option value="Male">Male</option><option value="Female">Female</option><option value="Male (neutered)">Male (neutered)</option><option value="Female (spayed)">Female (spayed)</option></select>',
  },
  {
    text: "Does your pet have any medical history (previous conditions, allergies, medications, surgeries, vaccinations)?",
    input: '<textarea class="form-control" id="medicalHistory" name="medical_history" rows="3" placeholder="e.g., Previous UTI, allergic to chicken, on heartworm prevention"></textarea>',
  },
  {
    text: "What symptoms is your pet experiencing? Please include onset, severity, duration, and patterns.",
    input: '<textarea class="form-control" id="symptoms" name="symptoms" rows="3" required placeholder="e.g., Vomiting for 2 days, lethargic, not eating"></textarea>',
  },
  {
    text: "Anything else to add (diet, environment, recent changes, stress, travel, family history of other pets)?",
    input: '<textarea class="form-control" id="otherInfo" name="other_info" rows="3" placeholder="e.g., Indoor cat, recent move, eats premium kibble"></textarea>',
  },
];

let currentQuestionIndex = 0;
const userResponses = {};
let chatActivated = false;

function addMessage(text, isUser = false) {
  const message = document.createElement("div");
  message.classList.add("chat-message", isUser ? "user-message" : "ai-message");
  if (!isUser) {
    const typingSpan = document.createElement("span");
    typingSpan.classList.add("typing");
    if (text.includes("<") && text.includes(">")) {
      typingSpan.innerHTML = text;
    } else {
      const lines = text.split("\n").map((line) => {
        const span = document.createElement("span");
        span.textContent = line;
        span.style.display = "block";
        return span;
      });
      lines.forEach((line) => typingSpan.appendChild(line));
    }
    message.appendChild(typingSpan);
  } else {
    message.textContent = text;
  }
  chatContainer.appendChild(message);
  if (chatActivated) {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  } else {
    chatContainer.scrollTop = 0;
  }

  const tooltipTriggerList = message.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggerList.forEach((el) => new bootstrap.Tooltip(el));
}

function showQuestion() {
  if (currentQuestionIndex >= questions.length) {
    submitDiagnosis();
    return;
  }
  const question = questions[currentQuestionIndex];
  addMessage(question.text);
  currentInput.innerHTML = `
    ${question.input}
    <button type="button" class="btn btn-primary" id="submitBtn">${currentQuestionIndex === questions.length - 1 ? "Get Diagnosis" : "Send"}</button>
  `;
  const inputElement = currentInput.querySelector("input, select, textarea");
  inputElement.focus();
  const submitBtn = currentInput.querySelector("#submitBtn");
  submitBtn.addEventListener("click", handleSubmit);

  inputElement.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  });

  const tooltipTriggerList = currentInput.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipTriggerList.forEach((el) => new bootstrap.Tooltip(el));
}

function handleSubmit() {
  const inputElement = currentInput.querySelector("input, select, textarea");
  const value = inputElement.value.trim();
  const isRequired = inputElement.hasAttribute("required");

  if (isRequired && !value) {
    inputElement.classList.add("is-invalid");
    return;
  }

  // Validate species input
  if (inputElement.name === "species") {
    const species = value.toLowerCase();
    if (species !== "cat" && species !== "dog") {
      inputElement.classList.add("is-invalid");
      // Show error message
      let errorMsg = currentInput.querySelector(".error-message");
      if (!errorMsg) {
        errorMsg = document.createElement("div");
        errorMsg.className = "error-message text-danger small mt-1";
        currentInput.appendChild(errorMsg);
      }
      errorMsg.textContent = "Please enter either 'cat' or 'dog'";
      return;
    }
  }

  inputElement.classList.remove("is-invalid");
  // Remove any error messages
  const errorMsg = currentInput.querySelector(".error-message");
  if (errorMsg) {
    errorMsg.remove();
  }

  const fieldName = inputElement.name;
  userResponses[fieldName] = value;
  addMessage(value, true);
  chatActivated = true;
  currentInput.innerHTML = "";
  currentQuestionIndex++;
  setTimeout(showQuestion, 800);
}

async function submitDiagnosis() {
  loading.style.display = "block";
  chatContainer.style.display = "none";
  inputArea.style.display = "none";
  results.style.display = "none";

  try {
    const diagnoseResponse = await fetch("/diagnose", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json"
      },
      body: JSON.stringify(userResponses),
    });
    const diagnoseData = await diagnoseResponse.json();

    if (diagnoseData.error) {
      throw new Error(diagnoseData.error);
    }

    let topDiagnosis = diagnoseData.diagnosis;
    if (topDiagnosis.startsWith("Top 3 possible diagnoses:")) {
      topDiagnosis = topDiagnosis.split(":")[1].split(",")[0].split("(")[0].trim();
    }

    const veterinaryResponse = await fetch("/veterinary-details", {
      method: "POST",
      headers: { 
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ 
        diagnosis: topDiagnosis,
        species: userResponses.species,
        breed: userResponses.breed || "mixed breed"
      }),
    });
    const veterinaryData = await veterinaryResponse.json();

    loading.style.display = "none";

    const isHighConfidence = !diagnoseData.diagnosis.includes("Top 3");
    const topLikelihood = parseInt(diagnoseData.conditions[0].likelihood) || 0;

    if (isHighConfidence) {
      const topCondition = diagnoseData.conditions[0];
      diagnosisResult.innerHTML = `
        <div class="diagnosis-item">
          <h4>${topCondition.name} (${topCondition.likelihood}% certainty)</h4>
          <p>${topCondition.explanation || "No explanation provided"}</p>
        </div>
      `;
    } else {
      const topThree = diagnoseData.conditions.slice(0, 3);
      diagnosisResult.innerHTML = topThree.map(condition => `
        <div class="diagnosis-item">
          <h4>${condition.name} (${condition.likelihood}% certainty)</h4>
          <p>${condition.explanation || "No explanation provided"}</p>
        </div>
      `).join("");
    }

    urgentResult.textContent = diagnoseData.urgent ? "Urgent veterinary attention required" : "Not urgent";
    urgentResult.className = diagnoseData.urgent ? "urgent" : "";
    consultResult.textContent = diagnoseData.consult;
    homecareResult.textContent = diagnoseData.homecare;

    if (veterinaryData.error || !veterinaryData.veterinary_details) {
      veterinaryResult.textContent = "No additional veterinary details available.";
    } else {
      const details = veterinaryData.veterinary_details;
      const cleanedPrevention = (details.Prevention || "Not available").replace(/\.,/g, ". ");
      veterinaryResult.innerHTML = `
        <h4>${veterinaryData.diagnosis} in ${veterinaryData.species}${veterinaryData.breed ? ` (${veterinaryData.breed})` : ''}</h4>
        <p><strong>Overview:</strong> ${details.Overview || "Not available"}</p>
        <p><strong>Symptoms:</strong> ${Array.isArray(details.Symptoms) ? "<ul>" + details.Symptoms.map(s => `<li>${s}</li>`).join("") + "</ul>" : (details.Symptoms || "Not available")}</p>
        <p><strong>When to see a veterinarian:</strong> ${details["When to see a veterinarian"] || "Not available"}</p>
        <p><strong>Causes:</strong> ${details.Causes || "Not available"}</p>
        <p><strong>Risk factors:</strong> ${Array.isArray(details["Risk factors"]) ? "<ul>" + details["Risk factors"].map(r => `<li>${r}</li>`).join("") + "</ul>" : (details["Risk factors"] || "Not available")}</p>
        <p><strong>Complications:</strong> ${details.Complications || "Not available"}</p>
        <p><strong>Prevention:</strong> ${cleanedPrevention}</p>
        <p><strong>Treatment options:</strong> ${details["Treatment options"] || "Not available"}</p>
      `;
    }

    results.classList.remove("shadow-sm", "results-green", "results-yellow", "results-red");
    if (diagnoseData.urgent) {
      results.classList.add("results-red");
    } else if (isHighConfidence && topLikelihood >= 50 && topLikelihood <= 75) {
      results.classList.add("results-yellow");
    } else {
      results.classList.add("results-green");
    }

    chatContainer.innerHTML = "";
    results.style.display = "block";
  } catch (error) {
    loading.style.display = "none";
    diagnosisResult.textContent = "Error: " + error.message;
    urgentResult.textContent = "";
    consultResult.textContent = "";
    homecareResult.textContent = "";
    veterinaryResult.textContent = "";
    results.classList.remove("shadow-sm", "results-green", "results-yellow", "results-red");
    results.classList.add("results-red");
    chatContainer.innerHTML = "";
    results.style.display = "block";
  }
}

function resetChat() {
  chatContainer.innerHTML = '';
  results.style.display = "none";
  inputArea.style.display = "block";
  chatContainer.style.display = "block";
  currentQuestionIndex = 0;
  chatActivated = false;
  Object.keys(userResponses).forEach(key => delete userResponses[key]);
  showQuestion();
}

editBtn.addEventListener("click", resetChat);

function forceScrollToTop() {
  window.scrollTo(0, 0);
  chatContainer.scrollTop = 0;
}

document.addEventListener("DOMContentLoaded", () => {
  forceScrollToTop();
  showQuestion();
});

window.addEventListener("load", () => {
  setTimeout(forceScrollToTop, 100);
});