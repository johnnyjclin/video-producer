/**
 * MD905Shorts v3 — NoirsBoxes 9:16 AI fast-cut shorts
 *
 * v3 changes from v2:
 *  - Source images are real brand photos (product-in-hand with real screen content)
 *  - Score overlays REMOVED — the real device screens already show "Inferior 89" / "Original 100"
 *  - Added 4 text_to_video B-roll scenes (cable, phone, swap, healthy) between product beats
 *  - Visual variety: 7 different Runway clips from 3 different source images + 4 text prompts
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  OffthreadVideo,
} from "remotion";

const FPS = 30;
const s = (sec: number) => Math.round(sec * FPS);

// Scene durations driven by measured TTS audio + visual minimums
// 1=hook, 2=problem, 3=reveal, 4=inferior, 5=swap, 6=original, 7=safe, 8=features, 9=cta
const SCENE_SECONDS = [2.0, 2.0, 3.0, 4.0, 2.0, 4.0, 1.5, 4.0, 4.0];
const START = SCENE_SECONDS.reduce<number[]>((acc, d, i) => {
  acc.push(i === 0 ? 0 : acc[i - 1] + SCENE_SECONDS[i - 1]);
  return acc;
}, []);
const TOTAL_SECONDS = SCENE_SECONDS.reduce((a, b) => a + b, 0);

const FONT_STACK =
  "'Nunito', 'Montserrat', 'SF Pro Display', -apple-system, sans-serif";

type Highlight = "pink" | "yellow" | "green" | "red";
const highlightBg: Record<Highlight, string> = {
  pink: "#FF3D8A",
  yellow: "#FFD60A",
  green: "#30D158",
  red: "#FF3B30",
};

type CaptionPart = { text: string; highlight?: Highlight };

// Brand caption — italic bold white with black stroke, colored highlight on emphasis
const BrandCaption: React.FC<{
  parts: CaptionPart[];
  topPx?: number;
  fontSize?: number;
  delay?: number;
}> = ({ parts, topPx = 200, fontSize = 76, delay = 0 }) => {
  const frame = useCurrentFrame();
  const local = frame - delay;
  const opacity = interpolate(local, [0, 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const t = spring({
    frame: local,
    fps: FPS,
    config: { damping: 14, stiffness: 160, mass: 0.8 },
  });
  const scale = interpolate(t, [0, 1], [0.85, 1]);
  return (
    <div
      style={{
        position: "absolute",
        top: topPx,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        opacity,
      }}
    >
      <div
        style={{
          maxWidth: "88%",
          textAlign: "center",
          transform: `scale(${scale})`,
          fontFamily: FONT_STACK,
          fontWeight: 900,
          fontStyle: "italic",
          fontSize,
          lineHeight: 1.15,
          color: "#FFFFFF",
          letterSpacing: -0.5,
          WebkitTextStroke: "2.5px #000000",
          textShadow:
            "0 0 8px #000, 0 4px 0 #000, 0 -4px 0 #000, 4px 0 0 #000, -4px 0 0 #000, 3px 3px 0 #000, -3px -3px 0 #000",
        }}
      >
        {parts.map((p, i) =>
          p.highlight ? (
            <span
              key={i}
              style={{
                backgroundColor: highlightBg[p.highlight],
                padding: "0 16px",
                borderRadius: 10,
                display: "inline-block",
                margin: "0 4px",
                color: "#FFFFFF",
                WebkitTextStroke: "2.5px #000000",
              }}
            >
              {p.text}
            </span>
          ) : (
            <span key={i}>{p.text}</span>
          ),
        )}
      </div>
    </div>
  );
};

// Video scene full-screen
const SceneVideo: React.FC<{ src: string }> = ({ src }) => (
  <AbsoluteFill style={{ backgroundColor: "#000" }}>
    <OffthreadVideo
      src={src}
      style={{ width: "100%", height: "100%", objectFit: "cover" }}
    />
  </AbsoluteFill>
);

// Kinetic typography scene (for non-product scenes when video gen unavailable)
const SceneKineticText: React.FC<{
  lines: { text: string; highlight?: Highlight }[];
  bgGlow?: string;
  fontSize?: number;
}> = ({ lines, bgGlow = "#FF3D8A", fontSize = 140 }) => {
  const frame = useCurrentFrame();
  const flash = interpolate(frame, [0, 5, 10], [1, 0.5, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A0A" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 50%, ${bgGlow}22 0%, #0A0A0A 70%)`,
        }}
      />
      <AbsoluteFill style={{ backgroundColor: "#FFFFFF", opacity: flash * 0.85 }} />
      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          padding: 60,
        }}
      >
        <div style={{ textAlign: "center" }}>
          {lines.map((line, i) => {
            const local = frame - 3 - i * 6;
            const t = spring({
              frame: local,
              fps: FPS,
              config: { damping: 12, stiffness: 150, mass: 0.9 },
            });
            const op = interpolate(local, [0, 5], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const ty = interpolate(t, [0, 1], [40, 0]);
            const sc = interpolate(t, [0, 1], [0.9, 1]);
            return (
              <div
                key={i}
                style={{
                  opacity: op,
                  transform: `translateY(${ty}px) scale(${sc})`,
                  marginBottom: 6,
                  fontFamily: FONT_STACK,
                  fontSize,
                  fontWeight: 900,
                  fontStyle: "italic",
                  color: "#FFFFFF",
                  letterSpacing: -4,
                  lineHeight: 1,
                  WebkitTextStroke: "3px #000000",
                  textShadow:
                    "0 0 16px #000, 0 6px 0 #000, 0 -6px 0 #000, 6px 0 0 #000, -6px 0 0 #000",
                }}
              >
                {line.highlight ? (
                  <span
                    style={{
                      backgroundColor: highlightBg[line.highlight],
                      padding: "0 22px",
                      borderRadius: 14,
                      display: "inline-block",
                      color: "#FFFFFF",
                      WebkitTextStroke: "3px #000000",
                    }}
                  >
                    {line.text}
                  </span>
                ) : (
                  line.text
                )}
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// Features grid
const SceneFeatures: React.FC<{ studioImg: string }> = ({ studioImg }) => {
  const features = [
    { icon: "✓", text: "C48 to C94 chips" },
    { icon: "✓", text: "Any charger, any cable" },
    { icon: "✓", text: "Offline. Portable." },
    { icon: "✓", text: "Scored in seconds" },
  ];
  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A0A" }}>
      <AbsoluteFill
        style={{
          background: "radial-gradient(circle at 50% 30%, #1a1a1a 0%, #000 80%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 160,
          left: "50%",
          transform: "translateX(-50%)",
          width: "52%",
          filter: "drop-shadow(0 20px 60px rgba(255,61,138,0.3))",
        }}
      >
        <Img src={studioImg} style={{ width: "100%" }} />
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 160,
          left: 70,
          right: 70,
          display: "flex",
          flexDirection: "column",
          gap: 30,
        }}
      >
        {features.map((f, i) => {
          const Tick: React.FC = () => {
            const frame = useCurrentFrame();
            const local = frame - i * 6 - 3;
            const t = spring({
              frame: local,
              fps: FPS,
              config: { damping: 14, stiffness: 160, mass: 0.9 },
            });
            const op = interpolate(local, [0, 5], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const x = interpolate(t, [0, 1], [-80, 0]);
            return (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 24,
                  opacity: op,
                  transform: `translateX(${x}px)`,
                }}
              >
                <div
                  style={{
                    fontFamily: FONT_STACK,
                    fontSize: 60,
                    fontWeight: 900,
                    color: "#FFD60A",
                    width: 60,
                    textAlign: "center",
                  }}
                >
                  {f.icon}
                </div>
                <div
                  style={{
                    fontFamily: FONT_STACK,
                    fontSize: 56,
                    fontWeight: 900,
                    fontStyle: "italic",
                    color: "#FFFFFF",
                    letterSpacing: -1,
                    WebkitTextStroke: "2px #000",
                  }}
                >
                  {f.text}
                </div>
              </div>
            );
          };
          return <Tick key={i} />;
        })}
      </div>
    </AbsoluteFill>
  );
};

// Hero CTA with real brand logo
const SceneOutro: React.FC<{ studioImg: string; logo: string }> = ({
  studioImg,
  logo,
}) => {
  const frame = useCurrentFrame();
  const productScale = spring({
    frame,
    fps: FPS,
    config: { damping: 14, stiffness: 80, mass: 1.2 },
  });
  const logoOp = interpolate(frame, [s(0.3), s(0.7)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const modelOp = interpolate(frame, [s(0.9), s(1.3)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tagOp = interpolate(frame, [s(1.5), s(1.9)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const urlOp = interpolate(frame, [s(2.2), s(2.6)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A0A" }}>
      <AbsoluteFill
        style={{
          background: "radial-gradient(circle at 50% 50%, #1a1a1a 0%, #000 80%)",
        }}
      />
      {/* Real NoirsBoxes logo (white) top */}
      <div
        style={{
          position: "absolute",
          top: 110,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: logoOp,
          filter: "invert(1)",
        }}
      >
        <Img src={logo} style={{ width: 420, height: "auto" }} />
      </div>
      <div
        style={{
          position: "absolute",
          top: 300,
          left: "50%",
          transform: `translate(-50%, 0) scale(${0.75 + productScale * 0.15})`,
          width: "55%",
          filter: "drop-shadow(0 20px 80px rgba(255,61,138,0.35))",
        }}
      >
        <Img src={studioImg} style={{ width: "100%" }} />
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 440,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: FONT_STACK,
          fontSize: 160,
          fontWeight: 900,
          fontStyle: "italic",
          color: "#FFFFFF",
          letterSpacing: -5,
          lineHeight: 1,
          opacity: modelOp,
          WebkitTextStroke: "3px #000",
        }}
      >
        MD-905
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 300,
          left: 0,
          right: 0,
          textAlign: "center",
          opacity: tagOp,
        }}
      >
        <span
          style={{
            fontFamily: FONT_STACK,
            fontSize: 58,
            fontWeight: 900,
            fontStyle: "italic",
            color: "#FFFFFF",
            backgroundColor: "#FF3D8A",
            padding: "10px 26px",
            borderRadius: 14,
            WebkitTextStroke: "2px #000",
          }}
        >
          Know before you sell.
        </span>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 200,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: FONT_STACK,
          fontSize: 40,
          fontWeight: 600,
          color: "#C8C8C8",
          letterSpacing: 4,
          opacity: urlOp,
        }}
      >
        noirsboxes.com
      </div>
    </AbsoluteFill>
  );
};

export interface MD905ShortsProps {
  // Text-to-video B-roll scenes (non-product)
  tvCableBad: string;
  tvPhoneDying: string;
  tvCableSwap: string;
  tvPhoneHealthy: string;
  // Image-to-video scenes (from brand photos) — product beats
  ivDeviceReveal: string;
  ivInferiorPush: string;
  ivOriginalPush: string;
  // Static assets for Remotion scenes
  studioImg: string;
  logo: string;
  // Audio (per-scene TTS + music bed)
  music: string;
  vo1: string;
  vo2: string;
  vo3: string;
  vo4: string;
  vo5: string;
  vo6: string;
  vo7: string;
  vo8: string;
  vo9: string;
}

const SceneAudio: React.FC<{ src: string; children: React.ReactNode }> = ({
  src,
  children,
}) => (
  <>
    {children}
    <Audio src={staticFile(src)} volume={1.0} />
  </>
);

export const MD905Shorts: React.FC<MD905ShortsProps> = ({
  tvCableBad,
  tvPhoneDying,
  tvCableSwap,
  tvPhoneHealthy,
  ivDeviceReveal,
  ivInferiorPush,
  ivOriginalPush,
  studioImg,
  logo,
  music,
  vo1,
  vo2,
  vo3,
  vo4,
  vo5,
  vo6,
  vo7,
  vo8,
  vo9,
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <Audio src={staticFile(music)} volume={0.25} />

      {/* Scene 1 — hook: cable close-up (Runway gen4.5 text_to_video) */}
      <Sequence from={s(START[0])} durationInFrames={s(SCENE_SECONDS[0])}>
        <SceneAudio src={vo1}>
          <SceneVideo src={staticFile(tvCableBad)} />
          <BrandCaption
            parts={[
              { text: "This cable " },
              { text: "looked real.", highlight: "pink" },
            ]}
            delay={s(0.2)}
            fontSize={74}
          />
        </SceneAudio>
      </Sequence>

      {/* Scene 2 — problem: phone dying (gen4.5 text_to_video) */}
      <Sequence from={s(START[1])} durationInFrames={s(SCENE_SECONDS[1])}>
        <SceneAudio src={vo2}>
          <SceneVideo src={staticFile(tvPhoneDying)} />
          <BrandCaption
            parts={[
              { text: "But it was " },
              { text: "killing my phone.", highlight: "red" },
            ]}
            delay={s(0.2)}
            fontSize={70}
          />
        </SceneAudio>
      </Sequence>

      {/* Scene 3 — solution: device in hand (image_to_video from brand photo) */}
      <Sequence from={s(START[2])} durationInFrames={s(SCENE_SECONDS[2])}>
        <SceneAudio src={vo3}>
          <SceneVideo src={staticFile(ivDeviceReveal)} />
          <BrandCaption
            parts={[
              { text: "Tested it with " },
              { text: "NoirsBoxes.", highlight: "yellow" },
            ]}
            delay={s(0.2)}
            fontSize={68}
          />
        </SceneAudio>
      </Sequence>

      {/* Scene 4 — INFERIOR 89 (real device screen, no fake overlay) */}
      <Sequence from={s(START[3])} durationInFrames={s(SCENE_SECONDS[3])}>
        <SceneAudio src={vo4}>
          <SceneVideo src={staticFile(ivInferiorPush)} />
          <BrandCaption
            parts={[
              { text: "Inferior. " },
              { text: "89.", highlight: "red" },
            ]}
            delay={s(0.3)}
            fontSize={92}
          />
        </SceneAudio>
      </Sequence>

      {/* Scene 5 — swap: cable being inserted (gen4.5 text_to_video) */}
      <Sequence from={s(START[4])} durationInFrames={s(SCENE_SECONDS[4])}>
        <SceneAudio src={vo5}>
          <SceneVideo src={staticFile(tvCableSwap)} />
          <BrandCaption
            parts={[
              { text: "Swap to " },
              { text: "original.", highlight: "green" },
            ]}
            delay={s(0.2)}
            fontSize={76}
          />
        </SceneAudio>
      </Sequence>

      {/* Scene 6 — ORIGINAL 100 (real device screen) */}
      <Sequence from={s(START[5])} durationInFrames={s(SCENE_SECONDS[5])}>
        <SceneAudio src={vo6}>
          <SceneVideo src={staticFile(ivOriginalPush)} />
          <BrandCaption
            parts={[
              { text: "100. ", highlight: "green" },
              { text: "Perfect." },
            ]}
            delay={s(0.3)}
            fontSize={92}
          />
        </SceneAudio>
      </Sequence>

      {/* Scene 7 — safe: phone healthy charging (gen4.5 text_to_video) */}
      <Sequence from={s(START[6])} durationInFrames={s(SCENE_SECONDS[6])}>
        <SceneAudio src={vo7}>
          <SceneVideo src={staticFile(tvPhoneHealthy)} />
          <BrandCaption
            parts={[{ text: "Safe ", highlight: "green" }, { text: " again." }]}
            delay={s(0.1)}
            fontSize={88}
          />
        </SceneAudio>
      </Sequence>

      {/* Scene 8 — features */}
      <Sequence from={s(START[7])} durationInFrames={s(SCENE_SECONDS[7])}>
        <SceneAudio src={vo8}>
          <SceneFeatures studioImg={staticFile(studioImg)} />
        </SceneAudio>
      </Sequence>

      {/* Scene 9 — CTA with real logo */}
      <Sequence from={s(START[8])} durationInFrames={s(SCENE_SECONDS[8])}>
        <SceneAudio src={vo9}>
          <SceneOutro
            studioImg={staticFile(studioImg)}
            logo={staticFile(logo)}
          />
        </SceneAudio>
      </Sequence>
    </AbsoluteFill>
  );
};

export const md905ShortsDuration = s(TOTAL_SECONDS);
