import CardSelector from "./common/CardSelector";
import FieldError from "./common/FieldError";

export type ProjectCategoryValue = 'large' | 'small' | 'contractor';

const projectCategories = [
  {
    label: 'Large project',
    description: 'Projects with more experienced users requiring full tool functionality',
    value: 'large',
    tooltip: 'The allocation of a project as a “Large Project” is at the discretion of your organisation and is subject to any internal policies and thresholds on the use of large vs small project reporting pathways.',
  },
  {
    label: 'Small project',
    description: 'Projects with less experienced users requiring only limited tool functionality',
    value: 'small',
    tooltip: 'The allocation of a project as a “Small Project” is at the discretion of your organisation and is subject to any internal policies and thresholds on the use of large vs small project reporting pathways.',
  },
  {
    label: 'Contractor or maintenance reporting',
    description: 'Simplified reporting of actual data on a specified frequency. For reporting from suppliers with ongoing contracts or internal maintenance teams with recurring activities.',
    value: 'contractor',
  },
];

type ProjectCategoryProps = {
  selectedCategory: ProjectCategoryValue | "";
  showerror?: string | null;
  onSelectCategory: (category: ProjectCategoryValue) => void;
};

const ProjectCategory: React.FC<ProjectCategoryProps> = ({
  selectedCategory,
  showerror,
  onSelectCategory, 
}) => {
  return (
    <div>
      <h2 className="mb-2 text-2xl text-text-base">
        Select project category
      </h2>
      <div className="mb-6 text-text-faint">
        Choose the category that best describes your project
      </div>
      {showerror && (<div>
        <FieldError message={showerror} />
      </div>)}

      <CardSelector
        options={projectCategories}
        selected={selectedCategory}
        onSelect={setSelectedCategory => onSelectCategory(setSelectedCategory as ProjectCategoryValue)}
      />
    </div>
  );
};

export default ProjectCategory;
