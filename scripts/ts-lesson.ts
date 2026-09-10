// Topic 2 - Typescript scratch

interface VisitDraft {
    ownerName: string;
    dogName: string;
    actualMinutes: number;
    conditionScore?: number; // optional
}

function describeVisit(draft: VisitDraft): string {
    const condition =
        draft.conditionScore === undefined
            ? "unscored"
            : `condition ${draft.conditionScore}`;
    return `${draft.ownerName} / ${draft.dogName}: ${draft.actualMinutes} min (${condition})`;
}

const example: VisitDraft = {
    ownerName: "Anna",
    dogName: "Bella",
    actualMinutes: 60,
    conditionScore: 3,
};

console.log(describeVisit(example));

// Uncomment to see TypeScript complain in the editor:
// const broken: VisitDraft = { ownerName: "Anna", dogName: "Bella", actualMinutes: "ninety" };