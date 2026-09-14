// const name = "Sebastian"; // cannot reassign name "..."
// let minutes = 60; // can change later: minutes = 90

// const name: string = "Sebastian"; // written explicitly but usually inferred as string

function greet1(who: string): string {
    return "Hello, " + who;
}

const greet2 = (who: string): string => {
    return `Hello, ${who}`;
};

console.log(greet1("Sebastian"));
console.log(greet2("Sebastian"));


// 1) Shape
interface Dog {
    name: string;
    minutes: number;
}

// 2) Functions
function summarize(dog: Dog): string {
    return `${dog.name} groomed for ${dog.minutes} min`;
}

function greet(who: string): string {
    return `Hello, ${who}`;
}

// 3) Values + run
const shop: string = "MuttMetrics";
const bella: Dog = { name: "Bella", minutes: 60 };

console.log(greet(shop));
console.log(summarize(bella));