// SPDX-License-Identifier: AGPL-3.0-only
// Keep the shared-memory X11 surface in the server's BGRA byte order.
// Scoped to the NAS renderer; the phone's Wayland graphics are unaffected.
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>

int nas_x11_set_format(void *window, int format)
    __asm__("_ZN15X11NativeWindow16setBuffersFormatEi");

int nas_x11_set_format(void *window, int format)
{
    static int (*original)(void *, int);
    if (!original) {
        void *library = dlopen(
            "/usr/lib/aarch64-linux-gnu/libhybris/eglplatform_x11.so",
            RTLD_NOW | RTLD_NOLOAD);
        original = library ? dlsym(library,
            "_ZN15X11NativeWindow16setBuffersFormatEi") : NULL;
    }
    if (!original) {
        fputs("NAS X11: original buffer-format handler unavailable\n", stderr);
        return -1;
    }
    // Android HAL: RGBA_8888=1, RGBX_8888=2, BGRA_8888=5.
    if (format == 1 || format == 2)
        format = 5;
    return original(window, format);
}
