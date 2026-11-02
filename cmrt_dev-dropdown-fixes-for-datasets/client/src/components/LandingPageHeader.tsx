import AustroadsLogo from "../assets/icons/Austroads-logo.png";

const LandingPageHeader = () => {
  return (
    <header className="h-[120px] bg-white border-b border-neutral-200 px-8 flex items-center">
      <div className="flex items-center gap-4">
        <img src={AustroadsLogo} alt="Austroads Logo" className="h-20 md:h-24 w-auto" />
        <span className="text-xl md:text-2xl lg:text-3xl font-normal text-text-dark">
          Carbon Measurement & Reporting Tool
        </span>
      </div>
    </header>
  );
};

export default LandingPageHeader;