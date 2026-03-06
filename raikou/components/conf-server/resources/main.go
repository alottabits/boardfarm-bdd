package main

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"github.com/pion/webrtc/v4"
)

// Session holds server-side RTCP stats for a single peer connection.
type Session struct {
	mu             sync.Mutex
	PacketsSent    uint64  `json:"packets_sent"`
	PacketsLost    uint64  `json:"packets_lost"`
	JitterMs       float64 `json:"jitter_ms"`
	RoundTripTimeMs float64 `json:"round_trip_time_ms"`
	Active         bool    `json:"active"`
}

var (
	sessions   = make(map[string]*Session)
	sessionsMu sync.RWMutex
	upgrader   = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}
)

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	publicIP := getEnv("PION_PUBLIC_IP", "172.16.0.12")
	port := getEnv("PION_PORT", "8443")
	certFile := getEnv("PION_CERT_FILE", "/certs/server.crt")
	keyFile := getEnv("PION_KEY_FILE", "/certs/server.key")

	portInt, _ := strconv.Atoi(port)

	settingEngine := webrtc.SettingEngine{}
	settingEngine.SetNAT1To1IPs([]string{publicIP}, webrtc.ICECandidateTypeHost)
	settingEngine.SetICEUDPMux(nil)

	udpListener, err := net.ListenPacket("udp4", fmt.Sprintf("0.0.0.0:%d", portInt))
	if err != nil {
		log.Fatalf("Failed to listen UDP on %d: %v", portInt, err)
	}
	iceMux := webrtc.NewICEUDPMux(nil, udpListener)
	settingEngine.SetICEUDPMux(iceMux)

	api := webrtc.NewAPI(webrtc.WithSettingEngine(settingEngine))

	mux := http.NewServeMux()

	// WebSocket signalling endpoint: /session_id
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		sessionID := r.URL.Path[1:]
		if sessionID == "" {
			http.Error(w, "session_id required in path", http.StatusBadRequest)
			return
		}

		// /stats/<session_id> endpoint for server-side RTCP stats
		if len(sessionID) > 6 && sessionID[:6] == "stats/" {
			sid := sessionID[6:]
			sessionsMu.RLock()
			s, ok := sessions[sid]
			sessionsMu.RUnlock()
			if !ok {
				http.Error(w, "session not found", http.StatusNotFound)
				return
			}
			s.mu.Lock()
			defer s.mu.Unlock()
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(s)
			return
		}

		handleWebSocket(w, r, api, sessionID, publicIP)
	})

	addr := fmt.Sprintf("0.0.0.0:%s", port)

	if _, err := os.Stat(certFile); err == nil {
		log.Printf("Starting WSS signalling on %s (TLS)", addr)
		tlsCert, err := tls.LoadX509KeyPair(certFile, keyFile)
		if err != nil {
			log.Fatalf("Failed to load TLS cert: %v", err)
		}
		server := &http.Server{
			Addr:    addr,
			Handler: mux,
			TLSConfig: &tls.Config{
				Certificates: []tls.Certificate{tlsCert},
				MinVersion:   tls.VersionTLS13,
			},
		}
		log.Fatal(server.ListenAndServeTLS("", ""))
	} else {
		log.Printf("No TLS cert at %s — starting plain WS on %s", certFile, addr)
		log.Fatal(http.ListenAndServe(addr, mux))
	}
}

func handleWebSocket(w http.ResponseWriter, r *http.Request, api *webrtc.API, sessionID, publicIP string) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("[%s] WebSocket upgrade failed: %v", sessionID, err)
		return
	}
	defer conn.Close()

	sess := &Session{Active: true}
	sessionsMu.Lock()
	sessions[sessionID] = sess
	sessionsMu.Unlock()

	defer func() {
		sess.mu.Lock()
		sess.Active = false
		sess.mu.Unlock()
	}()

	config := webrtc.Configuration{}

	pc, err := api.NewPeerConnection(config)
	if err != nil {
		log.Printf("[%s] Failed to create PeerConnection: %v", sessionID, err)
		return
	}
	defer pc.Close()

	// Echo back any received track
	pc.OnTrack(func(track *webrtc.TrackRemote, receiver *webrtc.RTPReceiver) {
		log.Printf("[%s] Track received: %s (%s)", sessionID, track.Codec().MimeType, track.Kind())

		localTrack, err := webrtc.NewTrackLocalStaticRTP(track.Codec().RTPCodecCapability, track.ID(), track.StreamID())
		if err != nil {
			log.Printf("[%s] Failed to create local track: %v", sessionID, err)
			return
		}

		sender, err := pc.AddTrack(localTrack)
		if err != nil {
			log.Printf("[%s] Failed to add track: %v", sessionID, err)
			return
		}

		// Read RTCP from sender (needed to keep the connection alive)
		go func() {
			for {
				if _, _, err := sender.Read(make([]byte, 1500)); err != nil {
					return
				}
			}
		}()

		// Forward RTP packets and collect stats
		go func() {
			buf := make([]byte, 1500)
			for {
				n, _, err := track.Read(buf)
				if err != nil {
					return
				}
				if _, err := localTrack.Write(buf[:n]); err != nil {
					return
				}
				sess.mu.Lock()
				sess.PacketsSent++
				sess.mu.Unlock()
			}
		}()
	})

	// Collect RTCP stats periodically
	go func() {
		ticker := time.NewTicker(1 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			stats := pc.GetStats()
			for _, s := range stats {
				if inbound, ok := s.(webrtc.InboundRTPStreamStats); ok {
					sess.mu.Lock()
					sess.PacketsLost = uint64(inbound.PacketsLost)
					sess.JitterMs = inbound.Jitter * 1000
					sess.mu.Unlock()
				}
				if remote, ok := s.(webrtc.RemoteInboundRTPStreamStats); ok {
					sess.mu.Lock()
					sess.RoundTripTimeMs = remote.RoundTripTime * 1000
					sess.mu.Unlock()
				}
			}
		}
	}()

	pc.OnICECandidate(func(c *webrtc.ICECandidate) {
		if c == nil {
			return
		}
		payload, _ := json.Marshal(map[string]interface{}{
			"type":      "candidate",
			"candidate": c.ToJSON(),
		})
		conn.WriteMessage(websocket.TextMessage, payload)
	})

	// Signalling loop: read SDP offer, send SDP answer, exchange ICE candidates
	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			log.Printf("[%s] WebSocket read: %v", sessionID, err)
			return
		}

		var signal map[string]interface{}
		if err := json.Unmarshal(msg, &signal); err != nil {
			continue
		}

		switch signal["type"] {
		case "offer":
			sdpStr, _ := json.Marshal(signal)
			var offer webrtc.SessionDescription
			json.Unmarshal(sdpStr, &offer)

			if err := pc.SetRemoteDescription(offer); err != nil {
				log.Printf("[%s] SetRemoteDescription failed: %v", sessionID, err)
				return
			}

			answer, err := pc.CreateAnswer(nil)
			if err != nil {
				log.Printf("[%s] CreateAnswer failed: %v", sessionID, err)
				return
			}

			if err := pc.SetLocalDescription(answer); err != nil {
				log.Printf("[%s] SetLocalDescription failed: %v", sessionID, err)
				return
			}

			payload, _ := json.Marshal(answer)
			conn.WriteMessage(websocket.TextMessage, payload)

		case "candidate":
			candidateData, _ := json.Marshal(signal["candidate"])
			var candidate webrtc.ICECandidateInit
			json.Unmarshal(candidateData, &candidate)
			pc.AddICECandidate(candidate)
		}
	}
}
