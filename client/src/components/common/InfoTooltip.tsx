
import React, { useEffect, useId, useRef, useState } from "react";
import infoFilledUrl from "../../assets/icons/info.svg";
import "./InfoTooltip.css";

type InfoTooltipProps = {
  label?: string;
  text?: string;
  content?: React.ReactNode;
  iconSize?: number;
  placement?: "right" | "left" | "top";
  trigger?: "hover" | "click" | "auto";
  className?: string;
  offset?: number;      // gap between icon and tooltip (px)
  maxWidth?: number;    // default 350
  minHeight?: number;   // default 0
  arrowOffset?: number; // shift arrow towards the icon (px)
  shiftX?: number
};

const InfoTooltip: React.FC<InfoTooltipProps> = ({
  label = "More information",
  text,
  content,
  iconSize = 20,
  placement = "top",
  trigger = "auto",
  className = "",
  offset = 8,
  maxWidth = 350,
  shiftX = 0,
  minHeight = 0,
  arrowOffset = 0,
}) => {
  const [open, setOpen] = useState(false);
  const [alignLeft, setAlignLeft] = useState(placement === "left");
  const btnRef = useRef<HTMLButtonElement | null>(null);
  const popRef = useRef<HTMLDivElement | null>(null);
  const id = useId();

  const isTouch =
    typeof window !== "undefined" && matchMedia("(pointer: coarse)").matches;
  const effectiveTrigger = trigger === "auto" ? (isTouch ? "click" : "hover") : trigger;

  const onEnter = () => {
    if (effectiveTrigger === "hover") setOpen(true);
  };
  const onLeave = () => {
    if (effectiveTrigger === "hover") setOpen(false);
  };
  const onClick = (e: React.MouseEvent) => {
    if (effectiveTrigger !== "click") return;
    e.stopPropagation();
    setOpen((o) => !o);
  };

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (btnRef.current?.contains(t) || popRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const check = () => {
      const btn = btnRef.current;
      const pop = popRef.current;
      if (!btn || !pop) return;

      if (placement === "top") {
        setAlignLeft(false);
        return;
      }
      const btnRect = btn.getBoundingClientRect();
      const spaceRight = window.innerWidth - btnRect.right;
      const needLeft = spaceRight < pop.offsetWidth + offset + 12;
      setAlignLeft(needLeft || placement === "left");
    };
    check();
    window.addEventListener("resize", check);
    window.addEventListener("scroll", check, true);
    return () => {
      window.removeEventListener("resize", check);
      window.removeEventListener("scroll", check, true);
    };
  }, [open, offset, placement]);

  // Positioning
  let popupStyle: React.CSSProperties;
  if (placement === "top") {
    popupStyle = {
      position: "absolute",
      bottom: `calc(100% + ${offset}px)`,
      left: "-80%",
      transform: `none`,
      // marginLeft: shiftX,
    };
  } else {
    popupStyle = {
      position: "absolute",
      top: "50%",
      transform: "translateY(-50%)",
      [alignLeft ? "right" : "left"]: `calc(100% + ${shiftX}px)`,
    } as React.CSSProperties;
  }

  

const arrowStyle: React.CSSProperties =
    placement === "top"
      ? {
          left: arrowOffset,
          
        }
      : {
          top: `calc(50% + ${arrowOffset}px)`,
          transform: "translateY(-50%)",
        };



  const arrowClass =
    placement === "top"
      ? "itp__arrow--bottom"
      : alignLeft
      ? "itp__arrow--right"
      : "itp__arrow--left";

  return (
    <span
      className={`itp-root relative inline-flex ${className}`}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      {/* ICON BUTTON */}
      <button
        type="button"
        ref={btnRef}
        aria-label={label}
        aria-describedby={open ? id : undefined}
        className="itp__icon-btn cursor-pointer"
        onClick={onClick}
        style={{ width: iconSize, height: iconSize }}
      >
        <img
          src={infoFilledUrl}
          alt=""
          aria-hidden="true"
          width={iconSize}
          height={iconSize}
          className="block w-full h-full"
        />
      </button>

      {/* TOOLTIP PANEL */}
  
{/* TOOLTIP */}
{open && (content || text) && (
  <div ref={popRef} role="tooltip" id={id} className="itp" style={{ ...popupStyle,maxWidth}}>
    <div
      className="itp__content"
      style={{
        maxWidth: "100%",              // cap width so it stays horizontal
        minHeight,             // optional
        whiteSpace: "normal",  // wrap content
        wordBreak: "break-word",
        display: "inline-block",
      }}
    >
      {content ?? text}
    </div>

    {/* Arrow */}
    <span
      className={`itp__arrow ${arrowClass}`}
      style={arrowStyle}
      aria-hidden="true"
    />
  </div>
)}

    </span>
  );
};

export default InfoTooltip;

