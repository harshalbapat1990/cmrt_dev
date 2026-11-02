import React from "react";

type CardProps = {
    status: string;
    date?: string;
    carbonValue?: number; 
    data?: React.ReactNode;
    onClick?: () => void;
    className?: string;
    isSelected?: boolean; 
};

const getStatusStyles = (status: string) => {
    switch (status.toLowerCase()) {
        case "not started":
            return {
                border: "border-2 border-primary",
                text: "text-text-base",
                icon: "radio_button_unchecked",
                iconClass: "text-text-base",
                bg: "bg-primary-weak",
                dot: "bg-primary"
            };
        case "in progress":
            return {
                border: "border-2 border-in-progress",
                text: "text-in-progress",
                icon: "radio_button_partial",
                iconClass: "text-in-progress",
                bg: "bg-status-in-progress-bg",
                dot: "bg-in-progress"
            };
        case "awaiting approval":
            return {
                border: "border-2 border-awaiting",
                text: "text-awaiting",
                icon: "mark_email_read",
                iconClass: "text-awaiting",
                bg: "bg-awaiting-bg",
                dot: "bg-awaiting"
            };
        case "approved":
            return {
                border: "border-2 border-success",
                text: "text-success",
                icon: "check",
                iconClass: "text-success",
                bg: "bg-status-approved-bg",
                dot: "bg-success"
            };
        default:
            return {
                border: "border-2 border-neutral-90",
                text: "text-neutral-90",
                icon: "radio_button_unchecked",
                iconClass: "text-neutral-90",
                bg: "bg-neutral-50",
                dot: "bg-neutral-90"
            };
    }
};

const Card = ({ status, date, carbonValue: _carbonValue, data, onClick, className = "", isSelected = false }: CardProps) => {
    const { border, text, icon: _icon, iconClass: _iconClass, bg, dot } = getStatusStyles(status);
    const cardBorder = isSelected ? border : "border-neutral-90";
    
    return (
        <div
            className={`text-sm font-medium text-text-dark border px-3 py-3 rounded-[var(--radius-3)] transition-colors cursor-pointer ${cardBorder} ${className}`}
            onClick={onClick}
        >
            <div className="flex items-center">
                <span className={`${text} ${bg} font-normal`}>{status}</span>
                {isSelected && (
                    <span className={`ml-auto self-center w-2 h-2 rounded-full ${dot}`} />
                )}
            </div>
            <div className="flex pt-3 items-center">
                <span>{date || "-"}</span>
                {data}
            </div>
        </div>
    );
};

export default Card;