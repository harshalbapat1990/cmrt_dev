import React, { useEffect, useState, useRef } from 'react';
import Charts from "../../assets/icons/charts.png";
import UserGuideService from "@/services/UserGuide.service";

const LandingPage: React.FC = () => {
  const [guideUrl, setGuideUrl] = useState<string | null>(null);
  const [guideFilename, setGuideFilename] = useState<string>("CMRT-User-Guide.pdf");
  const blobUrlRef = useRef<string | null>(null);

  const triggerDownload = (url: string, filename: string) => {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadGuide = async () => {
    try {
      if (guideUrl) {
        triggerDownload(guideUrl, guideFilename);
        return;
      }

      const active = await UserGuideService.getActiveVersion();
      if (!active) return;

      const url = await UserGuideService.fetchFileBlobUrl(active.id);

      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }

      blobUrlRef.current = url;
      setGuideUrl(url);
      setGuideFilename(active.filename || "CMRT-User-Guide.pdf");

      triggerDownload(url, active.filename || "CMRT-User-Guide.pdf");
    } catch (error) {
      console.error("Failed to download user guide", error);
    }
  };

  useEffect(() => {
    return () => {
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
      }
    };
  }, []);


  return (
      <div className="h-screen flex flex-col lg:flex-row bg-text-base text-white overflow-hidden">
        <div
          className="
            w-full lg:w-[33%]
            flex flex-col
            px-4 sm:px-6 md:px-10 lg:px-12
            py-6 sm:py-8 md:py-10
            lg:flex-shrink-0
          "
        >
          <div className="text-2xl sm:text-3xl md:text-[36px] lg:text-[38px] 2xl:text-[48px] font-light leading-tight">
            Carbon Measurement &amp; Reporting Tool
          </div>
  
          <div className="text-base sm:text-lg md:text-xl font-light mt-4 sm:mt-6">
            The Austroads Carbon Measurement and Reporting Tool (CMRT) enables consistent
            estimation and reporting of greenhouse gas (GHG) emissions resulting
            from transport infrastructure projects, across Australia and New Zealand.
          </div>
  
          <div className="text-base sm:text-lg md:text-xl font-light mt-4 sm:mt-6">
            The tool is free to use for Austroads members and their suppliers.
          </div>
  
          <button
            type="button"
            onClick={handleDownloadGuide}
            className="mt-6 border border-white w-full p-3.5 font-medium flex items-center justify-center gap-2 hover:bg-[#E8E8E8] hover:text-black cursor-pointer"
          >
            <span>Download user guide</span>
            <span className="material-symbols-rounded">chevron_forward</span>
          </button>
  
          <button className="mt-4 border border-white w-full p-3.5 font-medium flex items-center justify-center gap-2 hover:bg-[#E8E8E8] hover:text-black cursor-pointer">
            View launch webinar
            <span className="material-symbols-rounded">chevron_forward</span>
          </button>
  
          {/* <div className="mb-4 pt-6 pb-2 text-sm md:text-base">
            For support or to report an issue, contact&nbsp;
            <span className="font-semibold">
              support@cmrt.austroads.com.au
            </span>
          </div> */}
        </div>
  
        {/* RIGHT PANEL — image, hidden on small screens */}
        <div className="hidden lg:flex flex-1 min-h-0 border border-dashed border-white/30 bg-black/20 mt-10">
          <img
            src={Charts}
            alt="Dashboard charts preview"
            className="w-full h-full object-contain pl-8"
          />
        </div>
      </div>
    );
};

export default LandingPage;