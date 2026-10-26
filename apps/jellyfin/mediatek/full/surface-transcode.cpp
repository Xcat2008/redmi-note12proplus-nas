#include "transport-stream.h"
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <GLES2/gl2ext.h>
#include <android/hardware_buffer.h>
#include <android/native_window.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <media/NdkImageReader.h>
#include <media/NdkMediaCodec.h>
#include <media/NdkMediaExtractor.h>
#include <media/NdkMediaFormat.h>
#include <signal.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <unistd.h>
#define CHECK(x)                                                               \
  do {                                                                         \
    if (!(x)) {                                                                \
      fprintf(stderr, "FAIL line=%d %s EGL=%x GL=%x\n", __LINE__, #x,          \
              eglGetError(), glGetError());                                    \
      exit(2);                                                                 \
    }                                                                          \
  } while (0)
static GLuint shader(GLenum type, const char *src) {
  GLuint s = glCreateShader(type);
  glShaderSource(s, 1, &src, 0);
  glCompileShader(s);
  GLint ok = 0;
  glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char msg[1024];
    glGetShaderInfoLog(s, sizeof msg, 0, msg);
    fprintf(stderr, "%s\n", msg);
  }
  CHECK(ok);
  return s;
}
int main(int argc, char **argv) {
  setbuf(stderr, nullptr);
  prctl(PR_SET_PDEATHSIG, SIGTERM);
  CHECK(argc >= 3);
  bool stream = !strcmp(argv[2], "-");
  FILE *report = stream ? stderr : stdout;
  int width = argc > 3 ? atoi(argv[3]) : 1280,
      height = argc > 4 ? atoi(argv[4]) : 720,
      bitrate = argc > 5 ? atoi(argv[5]) : 1500000;
  int64_t seekUs = argc > 6 ? strtoll(argv[6], nullptr, 10) : 0;
  int limit = argc > 7 ? atoi(argv[7]) : 180,
      gop = argc > 8 ? atoi(argv[8]) : 90;
  int fd = !strcmp(argv[1], "-") ? dup(STDIN_FILENO) : open(argv[1], O_RDONLY);
  CHECK(fd >= 0);
  struct stat st;
  CHECK(!fstat(fd, &st));
  CHECK(S_ISREG(st.st_mode));
  AMediaExtractor *ext = AMediaExtractor_new();
  CHECK(AMediaExtractor_setDataSourceFd(ext, fd, 0, st.st_size) == AMEDIA_OK);
  AMediaFormat *input = nullptr;
  size_t track = 0;
  for (; track < AMediaExtractor_getTrackCount(ext); track++) {
    auto *f = AMediaExtractor_getTrackFormat(ext, track);
    const char *m;
    if (AMediaFormat_getString(f, AMEDIAFORMAT_KEY_MIME, &m) &&
        !strncmp(m, "video/", 6)) {
      input = f;
      break;
    }
    AMediaFormat_delete(f);
  }
  CHECK(input);
  CHECK(AMediaExtractor_selectTrack(ext, track) == AMEDIA_OK);
  fprintf(report, "INPUT %s\n", AMediaFormat_toString(input));
  const char *mime;
  CHECK(AMediaFormat_getString(input, AMEDIAFORMAT_KEY_MIME, &mime));
  const char *decoder = !strcmp(mime, "video/avc")    ? "c2.mtk.avc.decoder"
                        : !strcmp(mime, "video/hevc") ? "c2.mtk.hevc.decoder"
                        : !strcmp(mime, "video/x-vnd.on2.vp9")
                            ? "c2.mtk.vp9.decoder"
                            : nullptr;
  CHECK(decoder);
  int32_t rate = 30;
  AMediaFormat_getInt32(input, AMEDIAFORMAT_KEY_FRAME_RATE, &rate);
  if (rate <= 0 || rate > 120)
    rate = 30;
  float requestedRate = argc > 9 ? strtof(argv[9], nullptr) : float(rate);
  CHECK(requestedRate >= 1.f && requestedRate <= 120.f);
  if (seekUs)
    CHECK(AMediaExtractor_seekTo(
              ext, seekUs, AMEDIAEXTRACTOR_SEEK_PREVIOUS_SYNC) == AMEDIA_OK);
  int32_t iw = 0, ih = 0;
  CHECK(AMediaFormat_getInt32(input, AMEDIAFORMAT_KEY_WIDTH, &iw));
  CHECK(AMediaFormat_getInt32(input, AMEDIAFORMAT_KEY_HEIGHT, &ih));
  CHECK(width > 0 && height > 0 && width <= 3840 && height <= 2160 &&
        bitrate >= 64000 && bitrate <= 80000000);
  AImageReader *reader = nullptr;
  CHECK(AImageReader_newWithUsage(iw, ih, AIMAGE_FORMAT_PRIVATE,
                                  AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE, 4,
                                  &reader) == AMEDIA_OK);
  ANativeWindow *readwin = nullptr;
  CHECK(AImageReader_getWindow(reader, &readwin) == AMEDIA_OK);
  AMediaCodec *enc = AMediaCodec_createCodecByName("c2.mtk.avc.encoder");
  CHECK(enc);
  auto *fmt = AMediaFormat_new();
  AMediaFormat_setString(fmt, AMEDIAFORMAT_KEY_MIME, "video/avc");
  AMediaFormat_setInt32(fmt, AMEDIAFORMAT_KEY_WIDTH, width);
  AMediaFormat_setInt32(fmt, AMEDIAFORMAT_KEY_HEIGHT, height);
  AMediaFormat_setInt32(fmt, AMEDIAFORMAT_KEY_COLOR_FORMAT, 0x7f000789);
  AMediaFormat_setInt32(fmt, AMEDIAFORMAT_KEY_BIT_RATE, bitrate);
  AMediaFormat_setInt32(fmt, "bitrate-mode", 2);
  AMediaFormat_setFloat(fmt, AMEDIAFORMAT_KEY_FRAME_RATE, requestedRate);
  AMediaFormat_setFloat(fmt, AMEDIAFORMAT_KEY_I_FRAME_INTERVAL,
                        float(gop) / requestedRate);
  AMediaFormat_setInt32(fmt, "max-bframes", 0);
  CHECK(AMediaCodec_configure(enc, fmt, nullptr, nullptr,
                              AMEDIACODEC_CONFIGURE_FLAG_ENCODE) == AMEDIA_OK);
  ANativeWindow *encwin = nullptr;
  CHECK(AMediaCodec_createInputSurface(enc, &encwin) == AMEDIA_OK);
  EGLDisplay display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
  CHECK(display != EGL_NO_DISPLAY);
  EGLint major, minor;
  CHECK(eglInitialize(display, &major, &minor));
  EGLint attrs[] = {EGL_SURFACE_TYPE,
                    EGL_WINDOW_BIT,
                    EGL_RENDERABLE_TYPE,
                    EGL_OPENGL_ES2_BIT,
                    EGL_RED_SIZE,
                    8,
                    EGL_GREEN_SIZE,
                    8,
                    EGL_BLUE_SIZE,
                    8,
                    0x3142,
                    1,
                    EGL_NONE};
  EGLConfig config;
  EGLint count;
  CHECK(eglChooseConfig(display, attrs, &config, 1, &count) && count);
  EGLint ctxattrs[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
  EGLContext ctx = eglCreateContext(display, config, EGL_NO_CONTEXT, ctxattrs);
  CHECK(ctx != EGL_NO_CONTEXT);
  EGLSurface surface = eglCreateWindowSurface(display, config, encwin, nullptr);
  CHECK(surface != EGL_NO_SURFACE);
  CHECK(eglMakeCurrent(display, surface, surface, ctx));
  eglSwapInterval(display, 0);
  eglGetError();
  fprintf(report, "GPU vendor=%s renderer=%s version=%s\n",
          glGetString(GL_VENDOR), glGetString(GL_RENDERER),
          glGetString(GL_VERSION));
  auto createImage =
      (PFNEGLCREATEIMAGEKHRPROC)eglGetProcAddress("eglCreateImageKHR");
  auto destroyImage =
      (PFNEGLDESTROYIMAGEKHRPROC)eglGetProcAddress("eglDestroyImageKHR");
  auto nativeBuffer = (PFNEGLGETNATIVECLIENTBUFFERANDROIDPROC)eglGetProcAddress(
      "eglGetNativeClientBufferANDROID");
  auto bindImage = (PFNGLEGLIMAGETARGETTEXTURE2DOESPROC)eglGetProcAddress(
      "glEGLImageTargetTexture2DOES");
  auto timestamp = (PFNEGLPRESENTATIONTIMEANDROIDPROC)eglGetProcAddress(
      "eglPresentationTimeANDROID");
  CHECK(createImage && destroyImage && nativeBuffer && bindImage && timestamp);
  auto createSync =
      (PFNEGLCREATESYNCKHRPROC)eglGetProcAddress("eglCreateSyncKHR");
  auto destroySync =
      (PFNEGLDESTROYSYNCKHRPROC)eglGetProcAddress("eglDestroySyncKHR");
  auto dupFence = (PFNEGLDUPNATIVEFENCEFDANDROIDPROC)eglGetProcAddress(
      "eglDupNativeFenceFDANDROID");
  bool asyncFence = createSync && destroySync && dupFence &&
                    strstr(eglQueryString(display, EGL_EXTENSIONS),
                           "EGL_ANDROID_native_fence_sync");
  GLuint prog = glCreateProgram();
  glAttachShader(prog, shader(GL_VERTEX_SHADER,
                              "attribute vec2 a;attribute vec2 t;varying vec2 "
                              "v;void main(){gl_Position=vec4(a,0.,1.);v=t;}"));
  glAttachShader(
      prog, shader(GL_FRAGMENT_SHADER,
                   "#extension GL_OES_EGL_image_external : require\nprecision "
                   "mediump float;uniform samplerExternalOES tex;varying vec2 "
                   "v;void main(){gl_FragColor=texture2D(tex,v);}"));
  glLinkProgram(prog);
  GLint linked;
  glGetProgramiv(prog, GL_LINK_STATUS, &linked);
  CHECK(linked);
  glUseProgram(prog);
  const GLfloat xy[] = {-1, -1, 1, -1, -1, 1, 1, 1},
                uv[] = {0, 1, 1, 1, 0, 0, 1, 0};
  GLint a = glGetAttribLocation(prog, "a"), t = glGetAttribLocation(prog, "t");
  glVertexAttribPointer(a, 2, GL_FLOAT, GL_FALSE, 0, xy);
  glVertexAttribPointer(t, 2, GL_FLOAT, GL_FALSE, 0, uv);
  glEnableVertexAttribArray(a);
  glEnableVertexAttribArray(t);
  glViewport(0, 0, width, height);
  GLuint tex;
  glGenTextures(1, &tex);
  glBindTexture(GL_TEXTURE_EXTERNAL_OES, tex);
  glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
  glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
  glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_EXTERNAL_OES, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
  CHECK(AMediaCodec_start(enc) == AMEDIA_OK);
  auto *params = AMediaFormat_new();
  AMediaFormat_setInt32(params, "video-bitrate", bitrate);
  CHECK(AMediaCodec_setParameters(enc, params) == AMEDIA_OK);
  AMediaFormat_delete(params);
  AMediaCodec *dec = AMediaCodec_createCodecByName(decoder);
  CHECK(dec);
  CHECK(AMediaCodec_configure(dec, input, readwin, nullptr, 0) == AMEDIA_OK);
  CHECK(AMediaCodec_start(dec) == AMEDIA_OK);
  FILE *out = stream ? stdout : fopen(argv[2], "wb");
  CHECK(out);
  int fed = 0, decoded = 0, rendered = 0, encoded = 0;
  bool inputEOS = false, decoderEOS = false, encoderEOS = false,
       sentEncoderEOS = false;
  size_t bytes = 0;
  TransportStream mux(out);
  std::vector<uint8_t> codecConfig;
  fprintf(report,
          "READY decoder=%s encoder=c2.mtk.avc.encoder requested_bitrate=%d\n",
          decoder, bitrate);
  fflush(report);
  auto start = std::chrono::steady_clock::now();
  while (!encoderEOS) {
    if (!inputEOS) {
      ssize_t ix = AMediaCodec_dequeueInputBuffer(dec, 1000);
      if (ix >= 0) {
        size_t cap = 0;
        auto *p = AMediaCodec_getInputBuffer(dec, ix, &cap);
        CHECK(p);
        ssize_t n = limit && fed >= limit
                        ? -1
                        : AMediaExtractor_readSampleData(ext, p, cap);
        int64_t pts = n < 0 ? 0 : AMediaExtractor_getSampleTime(ext);
        CHECK(AMediaCodec_queueInputBuffer(
                  dec, ix, 0, n < 0 ? 0 : n, pts,
                  n < 0 ? AMEDIACODEC_BUFFER_FLAG_END_OF_STREAM : 0) ==
              AMEDIA_OK);
        if (n < 0)
          inputEOS = true;
        else {
          fed++;
          AMediaExtractor_advance(ext);
        }
      }
    }
    AMediaCodecBufferInfo bi;
    ssize_t ix = AMediaCodec_dequeueOutputBuffer(dec, &bi, 1000);
    if (ix >= 0) {
      bool valid = bi.size > 0 && bi.presentationTimeUs >= seekUs;
      decoderEOS = bi.flags & AMEDIACODEC_BUFFER_FLAG_END_OF_STREAM;
      CHECK(AMediaCodec_releaseOutputBuffer(dec, ix, valid) == AMEDIA_OK);
      if (valid) {
        decoded++;
        AImage *image = nullptr;
        media_status_t got;
        for (int tries = 0; tries < 100; tries++) {
          got = AImageReader_acquireNextImage(reader, &image);
          if (got == AMEDIA_OK)
            break;
          usleep(1000);
        }
        CHECK(image);
        AHardwareBuffer *buffer = nullptr;
        CHECK(AImage_getHardwareBuffer(image, &buffer) == AMEDIA_OK);
        EGLint imageattrs[] = {EGL_IMAGE_PRESERVED_KHR, EGL_TRUE, EGL_NONE};
        EGLImageKHR img =
            createImage(display, EGL_NO_CONTEXT, EGL_NATIVE_BUFFER_ANDROID,
                        nativeBuffer(buffer), imageattrs);
        CHECK(img != EGL_NO_IMAGE_KHR);
        bindImage(GL_TEXTURE_EXTERNAL_OES, img);
        CHECK(glGetError() == GL_NO_ERROR);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
        CHECK(glGetError() == GL_NO_ERROR);
        timestamp(display, surface, (bi.presentationTimeUs - seekUs) * 1000);
        CHECK(eglSwapBuffers(display, surface));
        int fence = -1;
        if (asyncFence) {
          EGLSyncKHR sync =
              createSync(display, EGL_SYNC_NATIVE_FENCE_ANDROID, nullptr);
          if (sync != EGL_NO_SYNC_KHR) {
            glFlush();
            fence = dupFence(display, sync);
            destroySync(display, sync);
          }
        }
        if (fence >= 0)
          AImage_deleteAsync(image, fence);
        else {
          glFinish();
          AImage_delete(image);
        }
        destroyImage(display, img);
        rendered++;
      }
    } else if (ix == AMEDIACODEC_INFO_OUTPUT_FORMAT_CHANGED) {
      auto *f = AMediaCodec_getOutputFormat(dec);
      fprintf(report, "DECODER_FORMAT %s\n", AMediaFormat_toString(f));
      AMediaFormat_delete(f);
    }
    if (decoderEOS && !sentEncoderEOS) {
      CHECK(AMediaCodec_signalEndOfInputStream(enc) == AMEDIA_OK);
      sentEncoderEOS = true;
    }
    while (true) {
      ssize_t ei = AMediaCodec_dequeueOutputBuffer(enc, &bi, 1000);
      if (ei >= 0) {
        size_t cap;
        auto *p = AMediaCodec_getOutputBuffer(enc, ei, &cap);
        if (bi.size) {
          CHECK(p && bi.offset + bi.size <= cap);
          if (bi.flags & AMEDIACODEC_BUFFER_FLAG_CODEC_CONFIG) {
            codecConfig.assign(p + bi.offset, p + bi.offset + bi.size);
            if (!stream)
              CHECK(fwrite(p + bi.offset, 1, bi.size, out) == (size_t)bi.size);
          } else {
            if (stream)
              CHECK(mux.frame(
                  p + bi.offset, bi.size, bi.presentationTimeUs + seekUs,
                  bi.flags & AMEDIACODEC_BUFFER_FLAG_KEY_FRAME, codecConfig));
            else
              CHECK(fwrite(p + bi.offset, 1, bi.size, out) == (size_t)bi.size);
            encoded++;
          }
          fflush(out);
          bytes += bi.size;
        }
        if (bi.flags & AMEDIACODEC_BUFFER_FLAG_END_OF_STREAM)
          encoderEOS = true;
        AMediaCodec_releaseOutputBuffer(enc, ei, false);
      } else {
        if (ei == AMEDIACODEC_INFO_OUTPUT_FORMAT_CHANGED) {
          auto *f = AMediaCodec_getOutputFormat(enc);
          fprintf(report, "ENCODER_FORMAT %s\n", AMediaFormat_toString(f));
          AMediaFormat_delete(f);
        }
        break;
      }
    }
    if (limit &&
        std::chrono::steady_clock::now() - start > std::chrono::seconds(40)) {
      fprintf(stderr, "TIMEOUT fed=%d decoded=%d rendered=%d encoded=%d\n", fed,
              decoded, rendered, encoded);
      break;
    }
  }
  fclose(out);
  double seconds =
      std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
          .count();
  fprintf(report,
          "RESULT fed=%d decoded=%d gpu_scaled=%d encoded=%d bytes=%zu "
          "seconds=%.3f fps=%.2f eos=%d\n",
          fed, decoded, rendered, encoded, bytes, seconds, encoded / seconds,
          encoderEOS);
  AMediaCodec_stop(dec);
  AMediaCodec_delete(dec);
  AMediaCodec_stop(enc);
  AMediaCodec_delete(enc);
  AImageReader_delete(reader);
  AMediaExtractor_delete(ext);
  close(fd);
  return encoderEOS ? 0 : 1;
}
