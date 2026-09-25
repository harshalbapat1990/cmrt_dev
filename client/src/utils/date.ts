
// utils/date.ts
export const getMonthLabelFromDate = (date: Date): string => {
  const formatter = new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' });
  return formatter.format(date); // "January 2026"
};

export const getNextMonthLabel = (currentLabel: string): string => {
  // currentLabel format: "November 2025"
  const [monthName, yearStr] = currentLabel.split(' ');
  const months = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December'
  ];
  const idx = months.indexOf(monthName);
  let year = parseInt(yearStr, 10);
  let nextIdx = idx + 1;
  if (nextIdx > 11) {
    nextIdx = 0;
    year += 1;
  }
  return `${months[nextIdx]} ${year}`;
};



// export function getNextMonthLabel(currentMonth: string): string {
//     const monthNames = [
//         "January", "February", "March", "April", "May", "June",
//         "July", "August", "September", "October", "November", "December"
//     ];

//     const parts = currentMonth.trim().split(" ");
//     if (parts.length !== 2) {
//         throw new Error("Invalid month format. Expected format: 'Month YYYY'");
//     }

//     const month = parts[0];
//     const year = parseInt(parts[1], 10);

//     const monthIndex = monthNames.indexOf(month);
//     if (monthIndex === -1) {
//         throw new Error("Invalid month name.");
//     }

//     const nextMonthIndex = (monthIndex + 1) % 12;
//     const nextYear = monthIndex === 11 ? year + 1 : year;

//     return `${monthNames[nextMonthIndex]} ${nextYear}`;
// }


// export function getMonthLabelFromDate(date: Date): string {
//   const monthNames = [
//     "January", "February", "March", "April", "May", "June",
//     "July", "August", "September", "October", "November", "December"
//   ];
//   return `${monthNames[date.getMonth()]} ${date.getFullYear()}`;
// }
