// SPDX-License-Identifier: AGPL-3.0-only
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net"
	"os"
	"os/exec"
	"os/signal"
	"regexp"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const ffmpeg = "/usr/lib/jellyfin-ffmpeg/ffmpeg"

type stream struct {
	Index    int    `json:"index"`
	Codec    string `json:"codec_name"`
	Width    int    `json:"width"`
	Height   int    `json:"height"`
	Rate     string `json:"r_frame_rate"`
	Pix      string `json:"pix_fmt"`
	Transfer string `json:"color_transfer"`
	Profile  string `json:"profile"`
	Field    string `json:"field_order"`
	SAR      string `json:"sample_aspect_ratio"`
	SideData []struct {
		Rotation float64 `json:"rotation"`
	} `json:"side_data_list"`
}

func value(args []string, key string) string {
	for i, a := range args {
		if a == key && i+1 < len(args) {
			return args[i+1]
		}
	}
	return ""
}
func number(s string) int { v, _ := strconv.Atoi(s); return v }
func seconds(s string) float64 {
	parts := strings.Split(s, ":")
	v := 0.
	for _, p := range parts {
		f, _ := strconv.ParseFloat(p, 64)
		v = v*60 + f
	}
	return v
}
func fallback(args []string, reason string) {
	if reason != "" {
		fmt.Fprintln(os.Stderr, "[Redmi video] Existing encoding path:", reason)
	}
	env := os.Environ()
	env = append(env, "LD_PRELOAD=/mediatek/libmediatek-dmabuf.so")
	syscall.Exec(ffmpeg, append([]string{ffmpeg}, args...), env)
	os.Exit(127)
}
func main() {
	args := os.Args[1:]
	if value(args, "-codec:v:0") != "h264_v4l2m2m" || value(args, "-f") != "hls" && value(args, "-hls_time") == "" {
		fallback(args, "")
		return
	}
	if lenAll(args, "-i") != 1 {
		fallback(args, "multiple inputs")
		return
	}
	path := strings.TrimPrefix(value(args, "-i"), "file:")
	if !strings.HasPrefix(path, "/") {
		fallback(args, "local files required")
		return
	}
	probe := exec.Command("/usr/lib/jellyfin-ffmpeg/ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=index,codec_name,width,height,r_frame_rate,pix_fmt,color_transfer,profile,field_order,sample_aspect_ratio:stream_side_data=rotation", "-of", "json", path)
	raw, err := probe.Output()
	var info struct {
		Streams []stream `json:"streams"`
	}
	if err != nil || json.Unmarshal(raw, &info) != nil || len(info.Streams) != 1 {
		fallback(args, "video probe failed")
		return
	}
	s := info.Streams[0]
	if s.Field != "" && s.Field != "unknown" && s.Field != "progressive" || s.SAR != "" && s.SAR != "N/A" && s.SAR != "1:1" {
		fallback(args, "interlaced or anamorphic media")
		return
	}
	for _, side := range s.SideData {
		if side.Rotation != 0 {
			fallback(args, "rotated media")
			return
		}
	}
	if s.Codec != "h264" && s.Codec != "hevc" && s.Codec != "vp9" || s.Pix != "yuv420p" || s.Transfer == "smpte2084" || s.Transfer == "arib-std-b67" {
		fallback(args, "unsupported codec or HDR format")
		return
	}
	vf := value(args, "-vf")
	if !allowedFilters(vf) {
		fallback(args, "additional video filters")
		return
	}
	if strings.Contains(vf, "subtitles") || strings.Contains(vf, "overlay") || strings.Contains(vf, "tonemap") || strings.Contains(vf, "transpose") || strings.Contains(vf, "crop=") {
		fallback(args, "video filter requires the existing path")
		return
	}
	re := regexp.MustCompile(`\\,([0-9]+)\)/([0-9]+)\)\*([0-9]+)`)
	m := re.FindStringSubmatch(vf)
	if len(m) != 4 || m[2] != m[3] {
		fallback(args, "unrecognized scale expression")
		return
	}
	align := number(m[2])
	maxWidth := number(m[1])
	if align < 2 || maxWidth < 64 {
		fallback(args, "invalid scale")
		return
	}
	width := int(math.Min(float64(s.Width), float64(maxWidth))) / align * align
	height := int(float64(width)*float64(s.Height)/float64(s.Width)/2) * 2
	bitrate := number(value(args, "-b:v"))
	seek := seconds(value(args, "-ss"))
	gop := number(value(args, "-g:v:0"))
	if gop == 0 {
		gop = 90
	}
	source, err := os.Open(path)
	if err != nil {
		fallback(args, "cannot open media")
		return
	}
	defer source.Close()
	conn, err := net.DialUnix("unix", nil, &net.UnixAddr{Name: "/mediatek/run/transcode.sock", Net: "unix"})
	if err != nil {
		fallback(args, "hardware broker unavailable")
		return
	}
	defer conn.Close()
	fps := strings.Split(s.Rate, "/")
	fpsN, fpsD := int64(30), int64(1)
	if len(fps) == 2 && number(fps[0]) > 0 && number(fps[1]) > 0 {
		fpsN = int64(number(fps[0]))
		fpsD = int64(number(fps[1]))
	}
	cfg, _ := json.Marshal(map[string]int64{"width": int64(width), "height": int64(height), "bitrate": int64(bitrate), "seek_us": int64(seek * 1000000), "gop": int64(gop), "fps_num": fpsN, "fps_den": fpsD})
	conn.SetDeadline(time.Now().Add(15 * time.Second))
	_, _, err = conn.WriteMsgUnix(cfg, syscall.UnixRights(int(source.Fd())), nil)
	if err != nil {
		fallback(args, "hardware request failed")
		return
	}
	reader := bufio.NewReader(conn)
	status, err := reader.ReadString('\n')
	if err != nil || status != "OK\n" {
		fallback(args, "hardware startup failed")
		return
	}
	conn.SetDeadline(time.Time{})
	r, w, err := os.Pipe()
	if err != nil {
		fallback(args, "pipe allocation failed")
		return
	}
	omit := map[string]bool{"-vf": true, "-b:v": true, "-maxrate": true, "-bufsize": true, "-level": true, "-force_key_frames:0": true, "-g:v:0": true, "-keyint_min:v:0": true, "-profile:v:0": true, "-pix_fmt": true}
	var modified []string
	for i := 0; i < len(args); i++ {
		a := args[i]
		if omit[a] && i+1 < len(args) {
			i++
			continue
		}
		if a == "-codec:v:0" {
			modified = append(modified, a, "copy")
			i++
			continue
		}
		if a == "-map" && i+1 < len(args) {
			mapValue := args[i+1]
			if mapValue == fmt.Sprintf("0:%d", s.Index) {
				mapValue = "1:0"
			}
			modified = append(modified, a, mapValue)
			i++
			continue
		}
		modified = append(modified, a)
		if a == "-i" && i+1 < len(args) {
			i++
			modified = append(modified, args[i], "-analyzeduration", "1000000", "-probesize", "100000", "-f", "mpegts", "-i", "pipe:3")
		}
	}
	fmt.Fprintf(os.Stderr, "[Redmi video] MediaTek decode -> Mali scale %dx%d -> MediaTek H.264 encode; FFmpeg remuxes video and handles audio\n", width, height)
	cmd := exec.Command(ffmpeg, modified...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.ExtraFiles = []*os.File{r}
	cmd.SysProcAttr = &syscall.SysProcAttr{Pdeathsig: syscall.SIGTERM}
	if err = cmd.Start(); err != nil {
		w.Close()
		r.Close()
		os.Exit(1)
	}
	r.Close()
	done := make(chan struct{})
	go func() { io.Copy(w, reader); w.Close(); close(done) }()
	sigs := make(chan os.Signal, 2)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	go func() { sig := <-sigs; cmd.Process.Signal(sig); conn.Close(); w.Close() }()
	err = cmd.Wait()
	conn.Close()
	w.Close()
	if err != nil {
		if exit, ok := err.(*exec.ExitError); ok {
			os.Exit(exit.ExitCode())
		}
		os.Exit(1)
	}
}
func lenAll(args []string, key string) int {
	n := 0
	for _, a := range args {
		if a == key {
			n++
		}
	}
	return n
}
func allowedFilters(s string) bool {
	depth, start := 0, 0
	escaped := false
	check := func(part string) bool {
		name := strings.SplitN(part, "=", 2)[0]
		return name == "setparams" || name == "scale" || name == "format"
	}
	for i, c := range s {
		if escaped {
			escaped = false
			continue
		}
		if c == '\\' {
			escaped = true
			continue
		}
		if c == '(' {
			depth++
		}
		if c == ')' {
			depth--
		}
		if c == ',' && depth == 0 {
			if !check(s[start:i]) {
				return false
			}
			start = i + 1
		}
	}
	return depth == 0 && check(s[start:])
}
