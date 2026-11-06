document.documentElement.dataset.appReady = "true";

const instrumentSelect = document.querySelector("[data-instrument-select]");
const sendValue = document.querySelector("[data-send-value]");
const rangeHint = document.querySelector("[data-range-hint]");

if (instrumentSelect && sendValue && rangeHint) {
	const updateInstrumentRange = () => {
		const option = instrumentSelect.selectedOptions[0];
		if (!option || !option.value) {
			sendValue.removeAttribute("min");
			sendValue.removeAttribute("max");
			rangeHint.textContent = "El rango permitido depende del instrumento seleccionado.";
			return;
		}

		sendValue.min = option.dataset.min;
		sendValue.max = option.dataset.max;
		rangeHint.textContent = `Rango: ${option.dataset.min} a ${option.dataset.max} ${option.dataset.unit}. Resolución BNR: ${option.dataset.scale}; Label: ${option.dataset.label}; SDI: ${option.dataset.sdi}; SSM: ${option.dataset.ssm}.`;
	};

	instrumentSelect.addEventListener("change", updateInstrumentRange);
	updateInstrumentRange();
}

document.querySelectorAll("[data-transmission-mode]").forEach((modeSelect) => {
	const portSelect = modeSelect.form.querySelector("[data-transmission-port]");
	const updatePortAvailability = () => {
		const usesPort = modeSelect.value === "uart";
		portSelect.disabled = !usesPort;
		portSelect.required = usesPort;
		if (!usesPort) portSelect.selectedIndex = 0;
	};

	modeSelect.addEventListener("change", updatePortAvailability);
	updatePortAvailability();
});

function drawWaveform(canvas, samples) {
	const context = canvas.getContext("2d");
	const width = canvas.width;
	const height = canvas.height;
	const middle = height / 2;
	const scale = (height * 0.42) / 0.05;

	context.fillStyle = "#ffffff";
	context.fillRect(0, 0, width, height);
	context.strokeStyle = "#d7dad4";
	context.lineWidth = 1;
	context.beginPath();
	context.moveTo(0, middle);
	context.lineTo(width, middle);
	for (let bit = 0; bit <= 32; bit += 1) {
		const x = (bit / 32) * width;
		context.moveTo(x, 12);
		context.lineTo(x, height - 12);
	}
	context.stroke();

	context.strokeStyle = "#2f6655";
	context.lineWidth = 2;
	context.beginPath();
	samples.forEach((sample, index) => {
		const x = (index / (samples.length - 1)) * width;
		const y = middle - sample * scale;
		if (index === 0) context.moveTo(x, y);
		else context.lineTo(x, y);
	});
	context.stroke();
}

document.querySelectorAll("[data-audio-form]").forEach((form) => {
	const previewButton = form.querySelector("[data-preview-audio]");
	const deviceSelect = form.querySelector("[data-audio-device]");
	const modeSelect = form.querySelector("[data-audio-mode]");
	const amplitudeInput = form.querySelector("[data-audio-amplitude]");
	const amplitudeOutput = form.querySelector("[data-amplitude-output]");
	const previewedInput = form.querySelector("[data-previewed]");
	const status = form.querySelector("[data-waveform-status]");
	const meta = form.querySelector("[data-waveform-meta]");
	const canvas = form.querySelector(".waveform-canvas");

	const invalidatePreview = () => {
		previewedInput.value = "0";
		status.textContent = "Parámetros modificados; volvé a previsualizar.";
	};

	const updateAmplitude = () => {
		amplitudeOutput.value = Number(amplitudeInput.value).toFixed(3);
		amplitudeOutput.textContent = Number(amplitudeInput.value).toFixed(3);
		invalidatePreview();
	};

	amplitudeInput.addEventListener("input", updateAmplitude);
	deviceSelect.addEventListener("change", invalidatePreview);

	previewButton.addEventListener("click", async () => {
		previewButton.disabled = true;
		status.textContent = "Generando previsualización...";
		previewedInput.value = "0";
		try {
			const parameters = new URLSearchParams({ amplitude: amplitudeInput.value });
			if (deviceSelect.value) parameters.set("device", deviceSelect.value);
			const response = await fetch(`${previewButton.dataset.previewUrl}?${parameters}`);
			const preview = await response.json();
			if (!response.ok) throw new Error(preview.error || "No se pudo generar la señal.");
			drawWaveform(canvas, preview.muestras);
			meta.textContent = `32 bits · ${preview.muestras.length} muestras · ${preview.frecuencia_muestreo} Hz · ${preview.muestras_por_bit} muestras/bit · ${preview.ritmo_demostracion.toFixed(2)} bits/s de demostración · ${(preview.duracion_segundos * 1000).toFixed(2)} ms`;
			status.textContent = "Vista previa lista. No se emitió sonido.";
			previewedInput.value = "1";
		} catch (error) {
			status.textContent = error.message;
		} finally {
			previewButton.disabled = false;
		}
	});

	form.addEventListener("submit", (event) => {
		if (modeSelect.value === "reproducir" && previewedInput.value !== "1") {
			event.preventDefault();
			status.textContent = "Previsualizá la señal antes de reproducirla.";
		}
	});
});
