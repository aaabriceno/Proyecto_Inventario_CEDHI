// Fondo rotativo de ambientes del CEDHI en la pantalla de login.
// Solo se ejecuta en /login (no en el resto del sitio web).

(function () {
	if (!/^\/login/.test(window.location.pathname)) {
		return;
	}

	var base = "/assets/inventario_cedhi/images/Ambientes/";
	var imagenes = [
		"auditorio.jpg",
		"direccion.jpg",
		"oficina-administrativa.jpg",
		"sala-reuniones.jpg",
		"sala-tutoria.jpg",
		"sala-tutoria2.jpg",
		"taller-bartender-comedor.jpg",
		"topico.jpg",
		"topico2.jpg",
		"zona-lectura.jpg",
		"zona-lectura2.jpg",
		"ambiente-01.jpg",
		"ambiente-02.jpg",
		"ambiente-03.jpg",
		"ambiente-04.jpg",
		"ambiente-05.jpg",
		"ambiente-06.jpg",
		"ambiente-07.jpg",
	];

	// Mezcla simple para no mostrar siempre la misma primera foto
	for (var i = imagenes.length - 1; i > 0; i--) {
		var j = Math.floor(Math.random() * (i + 1));
		var tmp = imagenes[i];
		imagenes[i] = imagenes[j];
		imagenes[j] = tmp;
	}

	var overlay = document.createElement("div");
	overlay.className = "cedhi-login-overlay";

	var capaA = document.createElement("div");
	capaA.className = "cedhi-login-bg";
	var capaB = document.createElement("div");
	capaB.className = "cedhi-login-bg";

	document.body.appendChild(capaA);
	document.body.appendChild(capaB);
	document.body.appendChild(overlay);

	var capas = [capaA, capaB];
	var activa = 0;
	var indice = 0;

	function precargar(src) {
		var img = new Image();
		img.src = src;
	}

	function mostrar(src) {
		var entrante = capas[(activa + 1) % 2];
		var saliente = capas[activa];
		entrante.style.backgroundImage = "url('" + src + "')";
		entrante.classList.add("is-active");
		saliente.classList.remove("is-active");
		activa = (activa + 1) % 2;
	}

	function siguiente() {
		var src = base + encodeURIComponent(imagenes[indice]);
		mostrar(src);
		indice = (indice + 1) % imagenes.length;
		precargar(base + encodeURIComponent(imagenes[indice]));
	}

	siguiente();
	setInterval(siguiente, 6000);
})();
