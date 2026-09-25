// Add in AddNewProject component (top-level types):
export type Step3Errors = {
  projectSummary?: {
    projectName?: string | null;
    projectType?: string | null;
    projectTypecast?: string | null;
    projectLocation?: string | null;
  };
  costAndSchedule?: {
    commenceDate?: string | null;
    operationalLifeYears?: string | null;
    projectCapexM?: string | null;
  };
  deliveryPartners?: {
    constructionContract?: string | null;
    constructionOrg?: string | null;
  };
  
reportingBoundary?: {
    required?: string ;
  };

};

