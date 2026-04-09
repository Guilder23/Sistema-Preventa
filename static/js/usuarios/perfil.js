	(function () {
		function initPerfilFoto() {
			var input = document.getElementById('perfilFoto');
			if (!input) return;

			var btn = document.getElementById('perfilFotoBtn');
			if (btn) {
				btn.addEventListener('click', function () {
					input.click();
				});
			}

			input.addEventListener('change', function () {
				var file = input.files && input.files[0];
				if (!file) return;

				if (!file.type || !file.type.startsWith('image/')) {
					input.value = '';
					return;
				}

				var max = 2 * 1024 * 1024;
				if (file.size && file.size > max) {
					input.value = '';
					return;
				}

				var img = document.getElementById('perfilAvatarImg');
				var placeholder = document.getElementById('perfilAvatarPlaceholder');
				if (!img) return;

				var url = URL.createObjectURL(file);
				img.src = url;
				img.style.display = 'block';
				if (placeholder) placeholder.style.display = 'none';
			});
		}

		if (document.readyState === 'loading') {
			document.addEventListener('DOMContentLoaded', initPerfilFoto);
		} else {
			initPerfilFoto();
		}
	})();
    